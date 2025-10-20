# Generated migration for germination condition model update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('germination', '0001_initial'),
    ]

    operations = [
        # Remove old environmental parameter fields
        migrations.RemoveField(
            model_name='germinationcondition',
            name='temperature',
        ),
        migrations.RemoveField(
            model_name='germinationcondition',
            name='humidity',
        ),
        migrations.RemoveField(
            model_name='germinationcondition',
            name='light_hours',
        ),
        
        # Update climate field to use new choices
        migrations.AlterField(
            model_name='germinationcondition',
            name='climate',
            field=models.CharField(
                choices=[
                    ('I', 'Intermedio'),
                    ('W', 'Caliente'),
                    ('C', 'Frío'),
                    ('IW', 'Intermedio Caliente'),
                    ('IC', 'Intermedio Frío'),
                ],
                help_text='Tipo de clima durante la germinación',
                max_length=2
            ),
        ),
    ]