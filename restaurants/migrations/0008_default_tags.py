from django.db import migrations


def create_default_tags(apps, schema_editor):
    Tag = apps.get_model('restaurants', 'Tag')
    default_tags = [
        {'name': '데이트', 'emoji': '💑'},
        {'name': '혼밥',  'emoji': '🙋'},
        {'name': '회식',  'emoji': '🥂'},
        {'name': '뷰맛집', 'emoji': '🌅'},
        {'name': '가족모임', 'emoji': '👨‍👩‍👧'},
        {'name': '반려동물', 'emoji': '🐾'},
        {'name': '주차가능', 'emoji': '🚗'},
        {'name': '채식',  'emoji': '🌿'},
    ]
    for t in default_tags:
        Tag.objects.get_or_create(name=t['name'], defaults={'emoji': t['emoji']})


def delete_default_tags(apps, schema_editor):
    Tag = apps.get_model('restaurants', 'Tag')
    names = ['데이트', '혼밥', '회식', '뷰맛집', '가족모임', '반려동물', '주차가능', '채식']
    Tag.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0007_tag_restaurant_tags_restauranttag_menuitem'),
    ]

    operations = [
        migrations.RunPython(create_default_tags, delete_default_tags),
    ]
