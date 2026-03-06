from django.db import migrations


def create_default_categories(apps, schema_editor):
    Category = apps.get_model('restaurants', 'Category')
    default_categories = [
        '한식', '중식', '일식', '양식', '분식',
        '카페', '패스트푸드', '치킨', '피자', '기타',
    ]
    for name in default_categories:
        Category.objects.get_or_create(name=name)


def delete_default_categories(apps, schema_editor):
    Category = apps.get_model('restaurants', 'Category')
    names = ['한식', '중식', '일식', '양식', '분식',
             '카페', '패스트푸드', '치킨', '피자', '기타']
    Category.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0012_alter_category_id_alter_menuitem_id_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_categories, delete_default_categories),
    ]
