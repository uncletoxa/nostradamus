from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('matches', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TeamSupporter',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('team_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='supported_team',
                    to='matches.team')),
                ('user_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user',
                    to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(blank=True, default='')),
                ('photo', models.ImageField(blank=True, upload_to='avatars/')),
                ('previous_participant', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SupportedTeam',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('user_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='supported_teams',
                    to=settings.AUTH_USER_MODEL)),
                ('team_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='supporters',
                    to='matches.team')),
            ],
            options={
                'unique_together': {('user_id', 'team_id')},
            },
        ),
    ]
