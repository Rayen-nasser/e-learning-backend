# core/management/commands/wait_for_db.py
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Waits for the database to be available'

    def handle(self, *args, **kwargs):
        self.stdout.write("Waiting for the database to be available...")

        db_conn = connections['default']
        retries = 0
        max_retries = 5

        while retries < max_retries:
            try:
                db_conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database is ready!"))
                return
            except OperationalError:
                retries += 1
                self.stdout.write(self.style.WARNING(f"Attempt {retries}/{max_retries} failed..."))
                time.sleep(1)

        self.stdout.write(self.style.ERROR("Unable to connect to the database after retries."))
        return
