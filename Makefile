exec:
    sudo docker-compose up
    
complete_tasks:
    sudo docker container logs mantistable_celery_worker 2>&1 | grep "Task complete" | wc -l
