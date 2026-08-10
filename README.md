# HR Evaluation API (Django + DRF)

A role-aware HR evaluation backend system for managing employees, organizational placements, objectives & competencies, weighted scoring with frozen weights per evaluation, self-evaluations, activity logs/timeline, and JWT authentication.

## Tech Stack

- **Framework**: Django + Django REST Framework
- **Authentication**: JWT via SimpleJWT
- **Database**: PostgreSQL
- **Utilities**: django-filter for query params, WhiteNoise for static files
- **Deployment**: Replit

## Features

### Employee Management
- **Cached Organization Path**: Employees include `dept_path`, `direct_manager_name`, and `latest_placement_id` for fast list views
- **Organizational Hierarchy**: Track employee positions and reporting structure

### Evaluations
- **Multiple Types**: Annual, quarterly, and optional evaluation cycles
- **Weight Snapshots**: Frozen weights per evaluation to maintain consistency
- **Objectives & Competencies**: Auto weight distribution and scoring system
- **Self-Evaluations**: Employee-created evaluations separate from LM/HOD/HR workflow

### Activity Logging
- **Audit Trail**: Appendable activity log per evaluation
- **Tracking**: Records action, actor, and comments for full transparency

### Authentication & Authorization
- **JWT Authentication**: Bearer token with refresh & rotation
- **Role-Based Permissions**: 
  - ADMIN
  - HR
  - HOD (Head of Department)
  - LM (Line Manager)
  - EMP (Employee)

### API Features
- **Filtering & Search**: Query parameters for list endpoints
- **RESTful Design**: Standard REST conventions with DRF viewsets and routers

## Documentation References

- [Django REST Framework - Core Concepts](https://www.django-rest-framework.org/)
- [DRF Viewsets & Routers](https://www.django-rest-framework.org/api-guide/viewsets/)
- [WhiteNoise Static Files](http://whitenoise.evans.io/)
- [Replit Deployments](https://docs.replit.com/hosting/deployments/about-deployments)
- [pytest Basics](https://docs.pytest.org/)

## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- pip
