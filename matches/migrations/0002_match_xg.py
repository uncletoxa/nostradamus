from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='home_xg',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='guest_xg',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
    ]
