from collections import deque
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse

from apps.models import Package, Load, Trip, Truck, Driver


CITY_GRAPH = {
    "Karachi":    {"Hyderabad"},
    "Hyderabad":  {"Karachi", "Sukkur"},
    "Sukkur":     {"Hyderabad", "Multan", "Quetta"},
    "Quetta":     {"Sukkur"},
    "Multan":     {"Sukkur", "Lahore", "Faisalabad"},
    "Faisalabad": {"Multan", "Lahore"},
    "Lahore":     {"Multan", "Faisalabad", "Gujranwala"},
    "Gujranwala": {"Lahore", "Rawalpindi"},
    "Rawalpindi": {"Gujranwala", "Islamabad", "Peshawar"},
    "Islamabad":  {"Rawalpindi"},
    "Peshawar":   {"Rawalpindi"},
}


def bfs_path(graph, start, end):
    """
    Plain BFS. Since every road has the same 'weight' (1 hop),
    BFS automatically gives the shortest path. No Dijkstra needed.
    Returns a list of cities, e.g. ["Karachi", "Hyderabad", "Sukkur"]
    or None if there is no path.
    """
    if start == end:
        return [start]

    visited = {start}
    queue = deque([[start]])  

    while queue:
        path = queue.popleft()
        current_city = path[-1]

        for neighbor in graph.get(current_city, []):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None  



def _add_load_suggestion(suggestions, origin, destination, pkgs, weight):
    """Small helper so we don't repeat this dict 3 times."""
    suggestions.append({
        "origin": origin,
        "destination": destination,
        "package_ids": [p.id for p in pkgs],
        "package_count": len(pkgs),
        "total_weight_kg": weight,
    })


def suggest_loads(department):
    """
    Step 1: group packages that share the SAME origin and SAME destination.
    Step 2: figure out avg truck capacity (weight_carry) across all active trucks.
    Step 3: if a group's total weight is bigger than that average, SPLIT it
             into smaller batches, each staying under the average — instead
             of suggesting one giant load no truck can realistically take.
    """
    packages = Package.objects.filter(
        load__isnull=True,
        dispatcher_department=department
    )

    groups = {}
    for pkg in packages:
        key = (pkg.origin, pkg.destination)
        groups.setdefault(key, []).append(pkg)

    trucks = Truck.objects.filter(status="Active", dispatcher_department=department)
    capacities = [float(t.weight_carry) for t in trucks if t.weight_carry]
    avg_capacity = sum(capacities) / len(capacities) if capacities else None

    suggestions = []

    for (origin, destination), pkgs in groups.items():
        total_weight = sum(float(p.weight_kg) for p in pkgs)

        if not avg_capacity or total_weight <= avg_capacity:
            _add_load_suggestion(suggestions, origin, destination, pkgs, total_weight)
            continue

        batch, batch_weight = [], 0.0
        for pkg in pkgs:
            pkg_weight = float(pkg.weight_kg)

            if batch and (batch_weight + pkg_weight) > avg_capacity:
                _add_load_suggestion(suggestions, origin, destination, batch, batch_weight)
                batch, batch_weight = [], 0.0

            batch.append(pkg)
            batch_weight += pkg_weight

        if batch:
            _add_load_suggestion(suggestions, origin, destination, batch, batch_weight)

    return suggestions


def suggest_trips(department):
    """
    For each truck (one at a time):
      1. Look at every leftover load and find its BFS route.
      2. Pick the load with the LONGEST route as the "main direction"
         of this trip (in your example: Karachi -> Lahore).
      3. Max allowed weight = 80% of truck.weight_carry.
      4. Any other leftover load whose origin AND destination both sit
         on that same main route gets added too (e.g. Karachi->Hyderabad,
         Karachi->Multan are just waypoints on the Karachi->Lahore road).
      5. Whatever got used in this trip is REMOVED from the pool so the
         next truck only sees what's actually still left.
    """
    trucks = list(Truck.objects.filter(
        status="Active", dispatcher_department=department
    ))
    drivers = list(Driver.objects.filter(
        status="Active", dispatcher_department=department
    ))

    assigned_load_ids = set(
        Trip.objects.filter(status=Trip.Status.ACTIVE)
        .values_list("loads__id", flat=True)
    )

    available_loads = list(
        Load.objects.filter(
            dispatcher_department=department,
            status=Load.Status.Active
        ).exclude(id__in=assigned_load_ids)
    )

    suggestions = []
    driver_index = 0

    for truck in trucks:
        if not truck.weight_carry or not available_loads:
            continue  

        max_weight = float(truck.weight_carry) * 0.8

        routed_loads = []
        for load in available_loads:
            path = bfs_path(CITY_GRAPH, load.origin, load.destination)
            if path:
                routed_loads.append((load, path))

        if not routed_loads:
            continue  
        routed_loads.sort(key=lambda pair: len(pair[1]), reverse=True)
        base_load, main_path = routed_loads[0]

        trip_loads = [base_load]
        total_weight = float(base_load.weight_lbs or 0)

        for load, path in routed_loads[1:]:
            on_same_route = load.origin in main_path and load.destination in main_path
            if not on_same_route:
                continue

            load_weight = float(load.weight_lbs or 0)
            if total_weight + load_weight <= max_weight:
                trip_loads.append(load)
                total_weight += load_weight

        used_ids = {l.id for l in trip_loads}
        available_loads = [l for l in available_loads if l.id not in used_ids]

        suggested_driver = None
        if drivers:
            suggested_driver = drivers[driver_index % len(drivers)]
            driver_index += 1

        suggestions.append({
            "truck_id": truck.id,
            "truck_unit_number": truck.unit_number,
            "route": main_path,
            "load_ids": [l.id for l in trip_loads],
            "total_weight": total_weight,
            "max_allowed_weight_80pct": max_weight,
            "suggested_driver_id": suggested_driver.id if suggested_driver else None,
        })

    return suggestions



def get_department(user):
    from apps.models import dispatch_department
    return dispatch_department.objects.get(user=user)


class SuggestLoadsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department = get_department(request.user)
        suggestions = suggest_loads(department)
        return JsonResponse({"suggested_loads": suggestions}, status=200)


class SuggestTripsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department = get_department(request.user)
        suggestions = suggest_trips(department)
        return JsonResponse({"suggested_trips": suggestions}, status=200)


