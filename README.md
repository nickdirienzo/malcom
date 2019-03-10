# malcom
Built during Noisebridge's (SF Stupid Shit No One Needs And Terrible Ideas Hackathon)[https://www.meetup.com/noisebridge/events/258638768/?fbclid=IwAR2FxppM9DOchRSGShdgtov1q_e8ykU2qgizhOR1q4QQwPRgVxWAiPBGXpM].

Deliver messages in your distributed system using SF MTA transit solutions.

Expect messages to be delayed, but eventually make it to their destinations.

What are you even talking about?
================================



```
pipenv run python
>>> import enqueue
# Create tables
>>> enqueue.db.create_all()
# Seed tables with stops
>>> enqueue.load_stops('<listener_url>')
```
