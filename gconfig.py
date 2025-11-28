"""
author: Lan_zhijiang
date: 2024/06/27
desc: gunicorn config file (production environment)
issues:
    #34
"""

debug = False
reload = False

reload_engine = "inotify"

bind = "127.0.0.1:6000"  # ip binding (sock is optional)
pidfile = "logs/gunicorn.pid"

workers = 1

worker_class = "uvicorn.workers.UvicornWorker"
# http://www.uvicorn.org/deployment/#running-gunicorn-worker

loglevel = "debug"
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"

access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'


# 执行命令
# gunicorn -c gconfig.py main:app
# gunicorn -c gconfig.py main:app -k uvicorn.workers.UvicornWorker
