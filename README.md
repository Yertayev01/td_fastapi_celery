create_app is a factory function, which can be called multiple times, that returns a FastAPI app for us to use.

In get_settings, we used the FASTAPI_CONFIG env variable to control which configuration to use. For example, during development, DevelopmentConfig will be used and TestingConfig will be used during test.
I do not recommend pydantic BaseSettings here because it might cause Celery to raise [ERROR/MainProcess] pidbox command error: KeyError('__signature__') error when we launch Flower

We used config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL)) to set the database connection string.
Then, we used create_app to create a new fastapi_app instance to ensure the relevant models are loaded.
Finally, we added target_metadata = Base.metadata so that new models are discovered by Alembic.

So, when from project.users import users_router is called, the code in project/users/__init__.py will run. models.py will be imported as well.

main.py - uses create_app to create a new FastAPI app
project/__init__.py - Factory function
project/config.py - FastAPI config
"project/users" - relevant models and routes for Users

create_celery is a factory function that configures and then returns a Celery app instance.
Rather than creating a new Celery instance, we used current_app so that shared tasks will work as expected.
celery_app.config_from_object(settings, namespace="CELERY") means all celery-related configuration keys should be prefixed with CELERY_. For example, to configure the broker_url, we should use CELERY_BROKER_URL



RUN sed -i 's/\r$//g' /entrypoint is used to process the line endings of the shell scripts, which converts Windows line endings to UNIX line endings.
We copied the different service start shell scripts to the root directory of the final image.
Since the source code will be housed under the "/app" directory of the container (from the .:/app volume in the Docker Compose file), we set the working directory to /app.

We used a depends_on key for the web service to ensure that it does not start until both the redis and the db services are up. However, just because the db container is up does not mean the database is up and ready to handle connections. So, we can use a shell script called entrypoint to ensure that we can actually connect to the database before we spin up the web service.

We defined a postgres_ready function that gets called in loop. The code will then continue to loop until the Postgres server is available.
exec "$@" is used to make the entrypoint a pass through to ensure that Docker runs the command the user passes in (command: /start, in our case). For more, review this Stack Overflow answer.

This will spin up each of the containers based on the order defined in the depends_on option:

redis and db containers first
Then the web, celery_worker, celery_beat, and flower containers
Once the containers are up, the entrypoint scripts will execute and then, once Postgres is up, the respective start scripts will execute. The db migrations will be applied and the development server will run. The FastAPI app should then be available.

Once the images are built, spin up the containers in detached mode:

$ docker-compose up -d

If you run into problems, you can view the logs at:

$ docker-compose logs -f

To enter the shell of a specific container that's up and running, run the following command:

$ docker-compose exec <service-name> bash

--filter python tells watchfiles to only watch py files.
'celery -A main.celery worker --loglevel=info' is the command we want watchfiles to run
By default, watchfiles will watch the current directory and all subdirectories

By setting task_always_eager to True, tasks will be executed immediately (synchronously) instead of being sent to the queue (asynchronously), allowing you to debug the code within the task as you normally would (with breakpoints and print statements and what not) with any other code in your FastAPI app. This mode is recommended for use during testing as well.

So, we have a view which mimics a call to a third-party email marketing API with requests.post('https://httpbin.org/delay/5'). This view could degrade performance if you're sustaining heavy traffic.

Since requests is a synchronous library, one solution is to switch to a library that leverages asyncio, such as httpx or aiohttp. But in some cases, the third-party SDK is built without asyncio, so Celery is better option.

form_example_post view, a task called sample_task is enqueued and the task ID is returned. The task_status view can then be used to check the status of the task given the task ID.

Since we set bind to True, this is a bound task, so the first argument to the task will always be the current task instance (self). Because of this, we can call self.retry to retry the failed task.
Remember to raise the exception returned by the self.retry method to make it work.
By setting the countdown argument to 5, the task will retry after a 5 second delay.

In the previous chapter, when we integrated a third-party service, we used XHR short polling to check the task status. Short polling can be wasteful since it creates a lot of connections and queries. Plus, depending on the polling interval, there could be a delay between the task completing and the client updating.

The client sends an AJAX request to a FastAPI view to trigger a Celery task.
FastAPI returns a task_id which can be used to receive messages about the task.
The client then uses the task_id to create a WebSocket connection via ws://127.0.0.1:8010/ws/task_status/{task_id}.
When the FastAPI view receives the WebSocket request, it subscribes to task_id channel.
After the Celery task finishes processing, Celery sends a message to the channel, and all clients subscribed to the channel will receive the message as well.
The client closes the WebSocket and displays the result on the page.

asyncio_redis is a Redis client that supports asyncio, which Broadcaster requires.

We created a new instance of Broadcast, which will be only used by FastAPI, not the Celery worker.
In the startup event handler we established the connection while in shutdown we disconnected from it.

We used @ws_router.websocket("/ws/task_status/{task_id}") to declare a Websocket path. {task_id} is a path parameter.
In ws_task_status, we first accepted the connection, and then obtained the task ID. After that, we subscribed to the specific channel and sent the message to the browser if it exists.
update_celery_task_status should be called in the Celery worker after the task is finished.
The Celery worker will publish the task info to the channel through Redis.