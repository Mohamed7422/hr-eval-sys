import pytest
from uuid import uuid4
from django.utils import timezone
from django.contrib.auth import get_user_model
from evaluation_app.models import (
    Company, Employee, WeightsConfiguration,
    JobType, EmpStatus, ManagerialLevel
)

@pytest.fixture
def company(db):
    return Company.objects.create(
        name="Test Co",
        address="",
        industry="Software",
        size="SMALL",
    )

@pytest.fixture
def create_user(db):
    User = get_user_model()
    def _create_user(**kw):
        data = {
            "username": f"u_{uuid4().hex[:8]}",
            "email": f"{uuid4().hex[:8]}@test.local",
            "password": "pass12345",
            "name": "Test User",
            "role": "EMP",       # or Role.EMP if you import it
        }
        data.update(kw)
        return User.objects.create_user(**data)
    return _create_user

@pytest.fixture
def create_employee(db, company, create_user):
    def _create_employee(**kw):
        user = kw.pop("user", None) or create_user()
        defaults = dict(
            user=user,
            company=company,
            managerial_level=ManagerialLevel.IC,
            status=EmpStatus.ACTIVE,
            job_type=JobType.FULL_TIME,
            join_date=timezone.now().date(),
        )
        defaults.update(kw)
        return Employee.objects.create(**defaults)
    return _create_employee

@pytest.fixture
def create_weights(db):
    def _create_weights(**kw):
        defaults = dict(
            level_name=ManagerialLevel.IC,
            objective_weight=60,
            competency_weight=40,
            core_weight=20,
            leadership_weight=10,
            functional_weight=10,
        )
        defaults.update(kw)
        return WeightsConfiguration.objects.create(**defaults)
    return _create_weights
