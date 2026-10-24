from django.db import migrations

STATES = ('Active', 'Disabled', 'Booked', 'Cancelled')


def seed_states(apps, schema_editor):
    State = apps.get_model('base', 'State')
    for name in STATES:
        State.objects.get_or_create(name=name, defaults={'description': name})


def unseed_states(apps, schema_editor):
    State = apps.get_model('base', 'State')
    State.objects.filter(name__in=STATES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_states, unseed_states),
    ]
