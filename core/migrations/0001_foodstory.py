from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='FoodStory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('subtitle', models.CharField(blank=True, max_length=200)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='stories/')),
                ('external_url', models.URLField(blank=True, help_text='외부 기사 링크 (선택)')),
                ('badge', models.CharField(blank=True, help_text='예: HOT, NEW, 추천', max_length=30)),
                ('is_published', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0, help_text='숫자 낮을수록 먼저 표시')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['order', '-created_at'],
            },
        ),
    ]
