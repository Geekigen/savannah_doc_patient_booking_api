from django.db import migrations


def seed_forward(apps, schema_editor):
    from base.seed import seed_all

    seed_all()


def seed_reverse(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Token = apps.get_model('authtoken', 'Token')
    Doctor = apps.get_model('base', 'Doctor')
    Patient = apps.get_model('base', 'Patient')
    Slot = apps.get_model('base', 'Slot')

    Token.objects.filter(user__username='admin').delete()
    User.objects.filter(username='admin').delete()
    Slot.objects.filter(doctor__name__in=['Ada', 'Ben', 'Cara', 'Dan', 'Eve']).delete()
    Doctor.objects.filter(name__in=['Ada', 'Ben', 'Cara', 'Dan', 'Eve']).delete()
    Patient.objects.filter(name__in=['Grace', 'Ken', 'Lucy', 'Mo']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_alter_appointment_options_and_more'),
        ('authtoken', '0004_alter_tokenproxy_options'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
