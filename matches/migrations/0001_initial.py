import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('team_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=30)),
                ('code', models.CharField(max_length=3)),
                ('emoji_symbol', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('match_id', models.AutoField(primary_key=True, serialize=False)),
                ('start_time', models.DateTimeField()),
                ('home_score', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('guest_score', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('fixture_id', models.IntegerField(blank=True, default=None, null=True)),
                ('current_minute', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('is_playoff', models.BooleanField(default=False)),
                ('home_to_advance', models.BooleanField(blank=True, default=None, null=True)),
                ('status', models.CharField(
                    choices=[('FINISHED', 'FINISHED'), ('SCHEDULED', 'SCHEDULED'),
                             ('IN_PLAY', 'IN_PLAY'), ('PAUSED', 'PAUSED')],
                    default='SCHEDULED', max_length=15)),
                ('guest_team', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='match_guest_team', to='matches.team')),
                ('home_team', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='match_home_team', to='matches.team')),
            ],
        ),
    ]
