from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_messagereaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='chat/images/'),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='text',
            field=models.TextField(blank=True, max_length=1000),
        ),
    ]
