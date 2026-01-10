import uuid
from django.db import migrations, models

def gen_uuid(apps, schema_editor):
    Appointment = apps.get_model('bookingApp', 'Appointment')
    for row in Appointment.objects.all():
        row.reschedule_token = uuid.uuid4()
        row.save(update_fields=['reschedule_token'])

class Migration(migrations.Migration):

    dependencies = [
        ('bookingApp', '0002_profile_onesignal_player_id'), # This will be filled in already
    ]

    operations = [
        # 1. Add the field allowing nulls first
        migrations.AddField(
            model_name='appointment',
            name='reschedule_token',
            field=models.CharField(max_length=100, null=True),
        ),
        # 2. Run the function to create unique UUIDs for old data
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
        # 3. Now make it Unique and Not Null
        migrations.AlterField(
            model_name='appointment',
            name='reschedule_token',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]