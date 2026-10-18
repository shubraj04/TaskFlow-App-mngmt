"""Seed demo users and tasks: `python manage.py seed_demo` (idempotent)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tasks.domain.entities import TaskStatus
from apps.tasks.infrastructure.models import TaskModel

DEMO_PASSWORD = "Demo1234!"
USERS = [("alice", "alice@example.com"), ("bob", "bob@example.com"), ("carol", "carol@example.com")]


class Command(BaseCommand):
    help = "Create demo users (alice, bob, carol / Demo1234!) and sample tasks."

    def handle(self, *args, **options):
        User = get_user_model()
        users = {}
        for username, email in USERS:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[username] = user

        if TaskModel.objects.exists():
            self.stdout.write("Tasks already present, skipping task seed.")
            return

        today = timezone.now().date()
        alice, bob, carol = users["alice"], users["bob"], users["carol"]
        rows = [
            ("Write sprint report", "Summarise velocity and blockers.", TaskStatus.TODO, 2, alice, bob),
            (
                "Fix login redirect bug",
                "Users land on a blank page after login.",
                TaskStatus.IN_PROGRESS,
                1,
                alice,
                alice,
            ),
            ("Update onboarding docs", "", TaskStatus.TODO, 7, alice, carol),
            ("Review pull request #42", "Focus on the migration.", TaskStatus.COMPLETED, -1, bob, alice),
            ("Plan team offsite", "Venue, budget, agenda.", TaskStatus.TODO, 14, bob, None),
            ("Renew SSL certificate", "Expires next month.", TaskStatus.TODO, -3, alice, alice),
            ("Prepare demo data", "", TaskStatus.IN_PROGRESS, 3, carol, alice),
            ("Archive old tickets", "", TaskStatus.COMPLETED, -10, alice, None),
            ("Design settings page", "Wireframes first.", TaskStatus.TODO, 10, carol, bob),
            ("Set up monitoring alerts", "", TaskStatus.TODO, 5, alice, None),
            ("Customer interview notes", "", TaskStatus.IN_PROGRESS, 4, bob, bob),
            ("Quarterly budget check", "", TaskStatus.TODO, 21, alice, carol),
        ]
        for title, desc, st, offset, owner, assignee in rows:
            TaskModel.objects.create(
                title=title,
                description=desc,
                status=st.value,
                due_date=today + timedelta(days=offset),
                owner=owner,
                assignee=assignee,
                completed_at=timezone.now() if st == TaskStatus.COMPLETED else None,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(USERS)} users (password: {DEMO_PASSWORD}) and {len(rows)} tasks."
            )
        )
