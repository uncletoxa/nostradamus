# Nostradamus

Simple Django app for Predictors Competition. Includes accounts management,
predictions, matches models, results tracker, and odds scraper. 
Initially hosted on [nostradamus.ml](https://nostradamus.ml).


Match results (including live updates) powered by the dev-friendly football API [football-data.org](https://football-data.org)

## Deployment

### dev

```bash
docker-compose up -d --build 
```

```bash
docker-compose exec web python manage.py flush --no-input
docker-compose exec web python manage.py makemigrations matches predictions results accounts
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### prod

Change parameters inside `.env` files (except for `.env.dev`) to the actual ones and rename them - remove `.example` postfix

```bash
docker-compose -f docker-compose-prod.yml up -d --build
```

```bash
docker-compose exec web python manage.py createsuperuser
```

```bash
docker-compose -f docker-compose-prod.yml exec web python manage.py makemigrations matches predictions results accounts --noinput
```

```bash
docker-compose -f docker-compose-prod.yml exec web python manage.py migrate --noinput
```

```bash
docker-compose -f docker-compose-prod.yml exec web python manage.py collectstatic
```

### Acknowledgements

[@vitorfs](https://github.com/vitorfs) for [Django development guide](https://simpleisbetterthancomplex.com/series/beginners-guide)
[@mjhea0](https://github.com/mjhea0) for [Django dockerisation guide](https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/)
