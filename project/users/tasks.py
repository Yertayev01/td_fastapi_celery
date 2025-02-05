import random
import logging

import requests
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.signals import task_postrun, after_setup_logger
from celery.utils.log import get_task_logger
from project.database import db_context


logger = get_task_logger(__name__)


@shared_task
def divide(x, y):

    #debug
    # from celery.contrib import rdb
    # rdb.set_trace()

    import time
    time.sleep(5)
    return x / y

@shared_task()
def sample_task(email):
    from project.users.views import api_call

    api_call(email)

@shared_task(bind=True)
def task_process_notification(self):
    try:
        if not random.choice([0, 1]):
            # mimic random error
            raise Exception()

        # this would block the I/O
        requests.post("https://httpbin.org/delay/5")
    except Exception as e:
        logger.error("exception raised, it would be retry after 5 seconds")
        raise self.retry(exc=e, countdown=5)
    


@task_postrun.connect
def task_postrun_handler(task_id, **kwargs):
    from project.ws.views import update_celery_task_status
    async_to_sync(update_celery_task_status)(task_id)

    from project.ws.views import update_celery_task_status_socketio
    update_celery_task_status_socketio(task_id)


@shared_task(name="task_schedule_work")
def task_schedule_work():
    logger.info("task_schedule_work run")


@shared_task(name="default:dynamic_example_one")
def dynamic_example_one():
    logger.info("Example One")


@shared_task(name="low_priority:dynamic_example_two")
def dynamic_example_two():
    logger.info("Example Two")


@shared_task(name="high_priority:dynamic_example_three")
def dynamic_example_three():
    logger.info("Example Three")


@shared_task()
def task_send_welcome_email(user_pk):
    from project.users.models import User

    with db_context() as session:
        user = session.query(User).get(user_pk)
        logger.info(f'send email to {user.email} {user.id}')

@shared_task()
def task_test_logger():
    logger.info("test")

@after_setup_logger.connect()
def on_after_setup_logger(logger, **kwargs):
    formatter = logger.handlers[0].formatter
    file_handler = logging.FileHandler('celery.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)