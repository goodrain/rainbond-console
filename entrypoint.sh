#!/bin/bash
gunicorn goodrain_web.wsgi --max-requests=5000 --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
