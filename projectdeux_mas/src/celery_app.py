from celery import Celery

# Create the Celery app instance with a broker URL
app = Celery('projectdeux_mas', broker='pyamqp://guest@localhost//')

# Add the new configuration setting to retry connections on startup
app.conf.broker_connection_retry_on_startup = True

# Automatically discover tasks in the specified module
app.autodiscover_tasks(['src.tasks'])