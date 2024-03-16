from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('azbankgateways', '0004_auto_20211115_1500'),
    ]

    operations = [
        migrations.AddField(
            model_name='bank',
            name='is_checked',
            field=models.BooleanField(default=False),
        ),
    ]