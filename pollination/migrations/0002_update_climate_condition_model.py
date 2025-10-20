# Generated migration for climate condition model update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pollination', '0001_initial'),
    ]

    operations = [
        # Remove old fields
        migrations.RemoveField(
            model_name='climatecondition',
            name='weather',
        ),
        migrations.RemoveField(
            model_name='climatecondition',
            name='temperature',
        ),
        migrations.RemoveField(
            model_name='climatecondition',
            name='humidity',
        ),
        migrations.RemoveField(
            model_name='climatecondition',
            name='wind_speed',
        ),
        
        # Add new climate field
        migrations.AddField(
            model_name='climatecondition',
            name='climate',
            field=models.CharField(
                choices=[
                    ('I', 'Intermedio'),
                    ('W', 'Caliente'),
                    ('C', 'Frío'),
                    ('IW', 'Intermedio Caliente'),
                    ('IC', 'Intermedio Frío'),
                ],
                default='I',
                help_text='Tipo de clima durante la polinización',
                max_length=2
            ),
            preserve_default=False,
        ),
    ]