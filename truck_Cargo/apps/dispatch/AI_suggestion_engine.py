# AI suggestion engine for dispatchers. This is a separate module from the main dispatch app

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
    suggestions.append({
        "origin": origin,
        "destination": destination,
        "package_ids": [p.id for p in pkgs],
        "package_count": len(pkgs),
        "total_weight_kg": weight,
    })


def suggest_loads(department):

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


def _on_route(load, path):

    if load.origin not in path or load.destination not in path:
        return False
    return path.index(load.origin) < path.index(load.destination)


def _route_for_loads(loads):

    routes = []
    for load in loads:
        path = bfs_path(CITY_GRAPH, load.origin, load.destination)
        if path:
            routes.append(path)

    if not routes:
        return None

    return max(routes, key=len)


def _get_busy_truck_ids():

    return set(
        Trip.objects.filter(status__in=[Trip.Status.ACTIVE, Trip.Status.PLANNED])
        .exclude(truck__isnull=True)
        .values_list("truck_id", flat=True)
    )


def _get_busy_driver_ids():

    return set(
        Trip.objects.filter(status__in=[Trip.Status.ACTIVE, Trip.Status.PLANNED])
        .exclude(driver__isnull=True)
        .values_list("driver_id", flat=True)
    )


def check_existing_planned_trips(department, available_loads):

    planned_trips = Trip.objects.filter(
        status=Trip.Status.PLANNED,
        dispatcher_department=department
    ).select_related("truck", "driver").prefetch_related("loads")

    suggestions = []

    for trip in planned_trips:
        truck = trip.truck
        if not truck or not available_loads:
            continue

        if truck.status != Truck.Status.ACTIVE or not truck.weight_carry:
            continue

        current_loads = list(trip.loads.all())
        current_weight = sum(float(l.weight_lbs or 0) for l in current_loads)
        max_weight = float(truck.weight_carry) * 0.8

        remaining_capacity = max_weight - current_weight
        if remaining_capacity <= 0:
            continue

        main_path = _route_for_loads(current_loads)
        if not main_path:
            continue

        added_loads = []
        for load in available_loads:
            if not _on_route(load, main_path):
                continue

            load_weight = float(load.weight_lbs or 0)
            if current_weight + load_weight <= max_weight:
                added_loads.append(load)
                current_weight += load_weight

        if not added_loads:
            continue

        used_ids = {l.id for l in added_loads}
        available_loads = [l for l in available_loads if l.id not in used_ids]

        suggestions.append({
            "trip_id": trip.id,
            "truck_id": truck.id,
            "truck_unit_number": truck.unit_number,
            "driver_id": trip.driver.id if trip.driver else None,
            "route": main_path,
            "current_load_ids": [l.id for l in current_loads],
            "suggested_additional_load_ids": [l.id for l in added_loads],
            "total_weight_after": current_weight,
            "max_allowed_weight_80pct": max_weight,
        })

    return suggestions, available_loads


def suggest_trips(department):

    busy_truck_ids = _get_busy_truck_ids()
    busy_driver_ids = _get_busy_driver_ids()

    trucks = list(
        Truck.objects.filter(status="Active", dispatcher_department=department)
        .exclude(id__in=busy_truck_ids)
    )
    drivers = list(
        Driver.objects.filter(status="Active", dispatcher_department=department)
        .exclude(id__in=busy_driver_ids)
    )

    committed_load_ids = set(
        Trip.objects.filter(
            status__in=[Trip.Status.ACTIVE, Trip.Status.PLANNED]
        ).values_list("loads__id", flat=True)
    )

    available_loads = list(
        Load.objects.filter(
            dispatcher_department=department,
            status=Load.Status.Active
        ).exclude(id__in=committed_load_ids)
    )

    existing_trip_suggestions, available_loads = check_existing_planned_trips(
        department, available_loads
    )

    new_trip_suggestions = []
  
    available_drivers = list(drivers)

    for truck in trucks:
        if not truck.weight_carry or not available_loads:
            continue

        max_weight = float(truck.weight_carry) * 0.8

        routed_loads = []
        for load in available_loads:
  
            load_weight = float(load.weight_lbs or 0)
            if load_weight > max_weight:
                continue

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
            if not _on_route(load, main_path):
                continue

            load_weight = float(load.weight_lbs or 0)
            if total_weight + load_weight <= max_weight:
                trip_loads.append(load)
                total_weight += load_weight

        used_ids = {l.id for l in trip_loads}
        available_loads = [l for l in available_loads if l.id not in used_ids]

        suggested_driver = available_drivers.pop(0) if available_drivers else None

        new_trip_suggestions.append({
            "truck_id": truck.id,
            "truck_unit_number": truck.unit_number,
            "route": main_path,
            "load_ids": [l.id for l in trip_loads],
            "total_weight": total_weight,
            "max_allowed_weight_80pct": max_weight,
            "suggested_driver_id": suggested_driver.id if suggested_driver else None,
        })

    return {
        "existing_trip_suggestions": existing_trip_suggestions,
        "new_trip_suggestions": new_trip_suggestions,
    }


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
        result = suggest_trips(department)
        return JsonResponse({
            "existing_trip_suggestions": result["existing_trip_suggestions"],
            "new_trip_suggestions": result["new_trip_suggestions"],
        }, status=200)