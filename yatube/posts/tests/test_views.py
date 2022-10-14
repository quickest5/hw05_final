from http import HTTPStatus

from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post

from yatube.settings import POSTS_COUNT

User = get_user_model()
TEST_POSTS_COUNT = 13


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.post.author,
            text='Текст тестового комментария'
        )

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse(
                'posts:index'
            ): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug1'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': 'StasBasov'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': '1'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_create',
            ): 'posts/create.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': '1'}
            ): 'posts/post_detail.html',
            reverse(
                'about:author'
            ): 'about/author.html',
            reverse(
                'about:tech'
            ): 'about/tech.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (
            self.authorized_client.get(
                reverse(
                    'posts:post_detail',
                    kwargs={'post_id': f'{self.post.pk}'})
            )
        )
        self.assertEqual(response.context.get(
            'post').author.username, f'{self.post.author}')
        self.assertEqual(response.context.get(
            'post').text, f'{self.post.text}')
        self.assertEqual(response.context.get(
            'post').group.title, f'{self.group.title}')
        self.assertEqual(response.context.get(
            'comments')[0].text, PostPagesTests.comment.text)

    def test_form_post_create_edit_correct_context(self):
        """Шаблон form_post_create и edit
        сформированы с правильным контекстом."""
        pages = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': f'{self.post.pk}'}),
        ]
        for page in pages:
            response = self.author_client.get(page)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_posts_places(self):
        """
        при создании поста указать группу, и докинуть фотку
         то этот пост появляется
        на главной странице сайта,
        на странице выбранной группы,
        в профайле пользователя
        """
        self.group_x = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='test-slug3',
        )

        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group_x,
            image=self.post.image
        )
        reverse_things = (
            reverse(
                'posts:index'
            ),
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            ),
            reverse(
                'posts:group_list',
                kwargs={'slug': f'{self.group_x.slug}'}
            ),
        )
        for reverse_name in reverse_things:
            response = self.authorized_client.get(reverse_name)
            test_obj = response.context['page_obj'][0]
            self.assertEqual(
                test_obj.text, self.post.text
            )
            self.assertEqual(
                test_obj.group.title, self.group_x.title
            )
            self.assertEqual(
                test_obj.author.username, self.post.author.username
            )
            self.assertEqual(
                test_obj.image, self.post.image
            )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PAGE_TEST_OFFSET = 3
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = []
        for i in range(POSTS_COUNT + PaginatorViewsTest.PAGE_TEST_OFFSET):
            cls.post.append(
                Post.objects.create(
                    author=cls.user,
                    text=f'Тестовый пост {i}',
                    group=cls.group,
                )
            )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Stasbasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page(self):
        """проверка количества постов на первой странице"""
        reverse_list = [
            reverse(
                'posts:index'
            ),
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug1'}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': 'auth'}
            ),
        ]
        for reverse_name in reverse_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(
                    response.context['page_obj']
                ), POSTS_COUNT)

    def test_second_page(self):
        """проверка количества постов на второй странице"""
        reverse_list = [
            reverse(
                'posts:index'
            ),
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug1'}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': 'auth'}
            ),
        ]
        for reverse_name in reverse_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    PaginatorViewsTest.PAGE_TEST_OFFSET
                )


class CommentPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.post.author,
            text='Текст тестового комментария'
        )

    def setUp(self):
        self.user = User.objects.create_user(username='StasBasov')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_comment_write_guest(self):
        """проверка гостя на возможность писать комменты"""
        response = (
            self.guest_client.get(
                reverse(
                    'posts:add_comment',
                    kwargs={'post_id': f'{self.post.pk}'})
            )
        )
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            ('guest_client'
             ' не может ставить комменты')
        )


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.post.author,
            text='Текст тестового комментария'
        )

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_cache(self):
        post222 = Post.objects.create(
            author=self.user,
            text='Тестовый пост2',
            group=self.group,
        )
        reverse_list = [
            reverse(
                'posts:index'
            )
        ]
        for reverse_name in reverse_list:
            with self.subTest(reverse_name=reverse_name):
                cache.clear()
                responsebefore = self.authorized_client.get(
                    reverse_name
                ).content
                post222.delete()
                responseafter = self.authorized_client.get(
                    reverse_name
                ).content
                self.assertEqual(responsebefore, responseafter)
                cache.clear()
                response_afterclear = self.authorized_client.get(
                    reverse_name
                ).content
                self.assertNotEqual(responseafter, response_afterclear)


class FollowTests(TestCase):
    """тесты на подписки"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug1',
            description='test-slug2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.post.author,
            text='Текст тестового комментария'
        )

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post.author)

    def test_follow_authorized(self):
        """проверка авторизованного и
        на возможность подписываться и отписываться"""
        reverses = {
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author}
            ): True,
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post.author}
            ): False,
        }

        for key, value in reverses.items():
            with self.subTest(key=key):
                self.authorized_client.get(key)
                self.assertEqual(
                    Follow.objects.filter(
                        user=self.user,
                        author=self.post.author,
                    ).exists(), value
                )

    def test_after_follow_follow_index(self):
        """
        при создании поста указать группу, и докинуть фотку, и подписаться
         то этот пост появляется
        в разделе избранное
        """

        Follow.objects.create(
            user=self.user,
            author=self.post.author,
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.user,
                author=self.post.author,
            ).exists(), True)
        reverse_things = (
            reverse(
                'posts:follow_index'
            ),
        )
        for reverse_name in reverse_things:
            response = self.authorized_client.get(reverse_name)
            test_obj = response.context['page_obj'][0]
            self.assertEqual(
                test_obj.text, self.post.text
            )
            self.assertEqual(
                test_obj.group.title, self.group.title
            )
            self.assertEqual(
                test_obj.author.username, self.post.author.username
            )
            self.assertEqual(
                test_obj.image, self.post.image
            )
