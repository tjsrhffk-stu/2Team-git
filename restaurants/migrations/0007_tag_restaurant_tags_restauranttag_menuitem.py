from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0006_restaurant_break_time'),
    ]

    operations = [
        # 1. Tag 모델 먼저 생성
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('emoji', models.CharField(default='🏷️', max_length=10)),
            ],
        ),
        # 2. RestaurantTag 중간 테이블 생성 (Tag와 Restaurant 둘 다 존재해야 함)
        migrations.CreateModel(
            name='RestaurantTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('restaurant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='restaurant_tags', to='restaurants.restaurant')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurants.tag')),
            ],
            options={
                'unique_together': {('restaurant', 'tag')},
            },
        ),
        # 3. Restaurant에 tags ManyToManyField 추가 (through 테이블이 이미 존재해야 함)
        migrations.AddField(
            model_name='restaurant',
            name='tags',
            field=models.ManyToManyField(
                blank=True,
                related_name='restaurants',
                through='restaurants.RestaurantTag',
                to='restaurants.Tag',
            ),
        ),
        # 4. MenuItem 모델 생성
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('price', models.PositiveIntegerField(default=0, help_text='원 단위 가격')),
                ('description', models.CharField(blank=True, max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='restaurants/menus/')),
                ('category', models.CharField(
                    choices=[('main', '메인'), ('side', '사이드'), ('drink', '음료'), ('dessert', '디저트'), ('set', '세트')],
                    default='main',
                    max_length=20,
                )),
                ('is_available', models.BooleanField(default=True, help_text='판매 가능 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('restaurant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='menu_items', to='restaurants.restaurant')),
            ],
            options={
                'ordering': ['category', 'name'],
            },
        ),
    ]
