all: system-setup db-setup venv-setup django-setup gunicorn-setup nginx-setup cert-setup
clean: db-clean venv-clean gunicorn-clean nginx-clean cert-clean system-clean

system-setup:
	sudo add-apt-repository -y ppa:deadsnakes/ppa
	sudo apt update
	sudo apt -y upgrade
	sudo apt install -y python3.7 postgresql postgresql-contrib nginx supervisor python3-pip
	mkdir -p ~/run ~/logs

db-setup: system-setup
	sudo -H -u postgres bash -c " \
	createuser u_nostr \
	&& createdb db_nostr --owner u_nostr \
	&& psql -c \"ALTER USER u_nostr WITH PASSWORD '$(db_password)'\" " 

venv-setup: system-setup
	sudo pip3 install virtualenv
	virtualenv venv -p python3.7
	. venv/bin/activate && pip install -r requirements.txt

django-setup: venv-setup # make sure .env file settings are set up
	. venv/bin/activate && ( \
	python manage.py migrate; \
	python manage.py collectstatic --noinput; \
	python manage.py createsuperuser; )

gunicorn-setup: venv-setup
	sed 's|PROJECT_DIR|'"$$PWD"'|' gunicorn_start.sh.template > ~/gunicorn_start.sh
	chmod u+x ~/gunicorn_start.sh
	touch ~/logs/gunicorn.log
	sed 's|USERNAME|'"$$USER"'|' supervisor.conf.template > nostradamus.conf
	sudo mv nostradamus.conf /etc/supervisor/conf.d/nostradamus.conf
	sudo systemctl enable supervisor
	sudo systemctl start supervisor
	sudo supervisorctl reread
	sudo supervisorctl update

nginx-setup: venv-setup
	sed -e 's|USERNAME|'"$$USER"'|' -e 's|DOMAIN|'$(domain)'|' nginx_config.template > nostradamus_nginx_config
	sudo mv nostradamus_nginx_config /etc/nginx/sites-available/nostradamus
	sudo ln -s /etc/nginx/sites-available/nostradamus /etc/nginx/sites-enabled/nostradamus
	sudo rm -f /etc/nginx/sites-enabled/default
	sudo service nginx restart

cert-setup: nginx-setup
	sudo snap install core
	sudo snap refresh core
	sudo apt purge certbot
	sudo snap install --classic certbot
	sudo ln -s /snap/bin/certbot /usr/bin/certbot
	sudo certbot --nginx -n --agree-tos --domains $(domain)


db-clean:
	sudo -H -u postgres bash -c " \
	dropdb db_nostr \
	&& dropuser u_nostr "

system-clean:
	sudo apt purge -y python3.7 postgresql postgresql-contrib nginx supervisor python3-pip
	sudo apt -y autoremove
	sudo apt -y autoclean

venv-clean:
	sudo pip3 uninstall -y virtualenv
	sudo rm -rf venv
	sudo rm -rf ~/staticfiles

gunicorn-clean:
	rm -f ~/gunicorn_start.sh
	rm -f ~/logs/gunicorn* ~/run/gunicorn*
	sudo rm /etc/supervisor/conf.d/nostradamus.conf
	sudo supervisorctl reread
	sudo supervisorctl update

nginx-clean:
	sudo rm /etc/nginx/sites-available/nostradamus
	sudo rm /etc/nginx/sites-enabled/nostradamus
	rm -f ~/logs/nginx*
	sudo service nginx restart

cert-clean:
	sudo certbot --nginx rollback
	sudo rm /usr/bin/certbot
	sudo snap remove certbot


