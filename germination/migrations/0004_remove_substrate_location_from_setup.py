# Generated manually to remove substrate and location fields from GerminationSetup

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("germination", "0003_germinationsetup_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="germinationsetup",
            name="substrate",
        ),
        migrations.RemoveField(
            model_name="germinationsetup",
            name="location",
        ),
        migrations.RemoveField(
            model_name="germinationsetup",
            name="substrate_details",
        ),
    ]