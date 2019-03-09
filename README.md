# malcom
Manages MUNI buses to deliver messages

```
pipenv run python
>>> import enqueue
# Create tables
>>> enqueue.db.create_all()
# Seed tables with stops
>>> enqueue.load_stops('')
```
