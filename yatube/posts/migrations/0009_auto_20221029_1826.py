# Generated by Django 2.2.16 on 2022-10-29 13:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0008_post_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(
                blank=True, upload_to='media/', verbose_name='Изображение'
            ),
        ),
    ]
