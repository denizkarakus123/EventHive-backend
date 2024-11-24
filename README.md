# EventHive_backend

```pip install fastapi uvicorn bcrypt jwt python-decouple```

```uvicorn main:app --reload```


# CLEAN UP DATABASE

# Remove all entries in database that have a start date before Nov 24 
```DELETE FROM people_event WHERE event_id IN (SELECT id FROM events WHERE start_date < '2024-11-24');```

```DELETE FROM events WHERE start_date < '2024-11-24';```

# FIX EVENTS WHERE START_TIME=END_TIME
```UPDATE events SET end_date = end_date + INTERVAL '1 hour' WHERE start_date = end_date;```

# DELETE EVENTS WITH UGLY NAMES
```DELETE FROM events WHERE name = 'Security Sunday: Haiti''s Current Domestic Security Concerns';```

```DELETE FROM people_event WHERE event_id = (SELECT id FROM events WHERE name = 'Security Sunday: Colombia''s Domestic Economic and Security Concerns');```

```DELETE FROM events WHERE name = 'Security Sunday: Colombia''s Domestic Economic and Security Concerns'```

```DELETE FROM people_event WHERE event_id = 92;```
```DELETE FROM events WHERE id = 92;```



