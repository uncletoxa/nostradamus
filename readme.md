# Nostradamus

Simple Django app for Predictors Competition. Includes accounts management,
predictions, matches models, results tracker, and odds scraper. 
Initially hosted on [nostradamus.ml](https://nostradamus.ml).


Match results (including live updates) powered by the dev-friendly football API [football-data.org](https://football-data.org)

## Deployment

Application deployment is partly interactive during Django superuser creation and site certificate issuing. All other stuff is automated.
1. Add `.env` file containing all the needed parameters for service start — [ALLOWED_HOSTS](https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts), [SECRET_KEY](https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-SECRET_KEY), [DATABASE_URL](https://github.com/kennethreitz/dj-database-url#url-schema) ([DEBUG](https://docs.djangoproject.com/en/3.2/ref/settings/#debug) could be also useful) to root folder of the project, use  `.env_example` as a template.
2. Execute Make providing:
	* _db_password_ as the password for db for django user. The same you put in DATABASE_URL on the previous step.
	* _domain_ domain where your app will be hosted — your site's URL w/o `https://www` part. 

For example: ```make domain="nostradamus.ml" db_password="my_super_password"```

## Cleaning

`make clean -i` to clean everything that's got installed during deployment.

### Acknowledgements

@vitorfs for brilliant [Djange guide](https://simpleisbetterthancomplex.com/series/beginners-guide)
