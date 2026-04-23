from pathlib import Path

import pytest

from vrp_platform.bootstrap import bootstrap_platform
from vrp_platform.config import PlatformSettings
from vrp_platform.db import session_scope
from vrp_platform.domain.enums import ObjectiveMode, Role
from vrp_platform.integrations.travel import HaversineTravelMatrixProvider
from vrp_platform.optimizer.fallback import FallbackSolver
from vrp_platform.repos.events import EventRepository
from vrp_platform.repos.orders import OrderRepository
from vrp_platform.repos.planning import PlanningRepository
from vrp_platform.services.auth import AuthService
from vrp_platform.services.planning import PlanningService


MANIFEST = b"""order_id,customer_name,lat,lon,weight_kg,length_m,width_m,height_m,service_time_min,window_start_min,window_end_min,address,priority,fragile,orientation_locked
SO-3001,Bandra Boutique,19.0596,72.8295,150,1.10,0.80,0.50,15,540,660,Hill Road Bandra,2,false,false
SO-3002,Andheri Medical,19.1136,72.8697,220,1.20,0.80,0.60,20,570,720,Veera Desai Road Andheri,2,true,false
"""


def _settings(tmp_path: Path) -> PlatformSettings:
    return PlatformSettings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'platform.db'}",
        seed_demo_data=True,
        use_road_geometry=False,
    )


class ExplodingOptimizer:
    def solve(self, request):
        raise RuntimeError("boom")


def test_planning_service_falls_back_when_primary_optimizer_fails(tmp_path: Path):
    app = bootstrap_platform(_settings(tmp_path))
    app.ingest_manifest(MANIFEST)
    request = app.build_solve_request(ObjectiveMode.COST)

    with session_scope(app.session_factory) as session:
        service = PlanningService(
            optimizer=ExplodingOptimizer(),
            fallback_solver=FallbackSolver(HaversineTravelMatrixProvider(app.settings)),
            order_repo=OrderRepository(session),
            planning_repo=PlanningRepository(session),
            event_repo=EventRepository(session),
        )
        response = service.solve_plan(request)

    assert response.run_id.startswith("fallback-")
    assert response.metadata["solver"] == "fallback_nearest_neighbor"
    assert any("Main optimizer failed" in warning for warning in response.validation_warnings)

    snapshot = app.dispatcher_snapshot()
    assert snapshot.recent_runs[0].run_id == response.run_id


def test_auth_service_enforces_roles():
    auth = AuthService()
    user = auth.login("dispatcher", "dispatcher123")

    assert user.role == Role.DISPATCHER

    auth.require_role(user, {Role.DISPATCHER, Role.ADMIN})

    with pytest.raises(PermissionError):
        auth.require_role(user, {Role.DRIVER})
