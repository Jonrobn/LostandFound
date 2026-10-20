from io import BytesIO
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Comment, LostAndFoundItem


class LostAndFoundWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='owner',
            password='test-password-123',
        )
        self.other_user = user_model.objects.create_user(
            username='other',
            password='test-password-123',
        )
        self.item = LostAndFoundItem.objects.create(
            owner=self.owner,
            item_name='Test phone',
            description='A test item.',
            category='Electronics',
            location='Library',
            date_lost_found='2026-10-03',
        )
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_settings.enable()

    def tearDown(self):
        self.media_settings.disable()
        self.media_directory.cleanup()

    def test_only_lost_report_statuses_are_available(self):
        self.assertEqual(
            LostAndFoundItem.STATUS_CHOICES,
            [('Open', 'Open'), ('Resolved', 'Resolved')],
        )
        self.assertEqual(self.item.status, 'Open')

    def test_create_report_requires_login(self):
        response = self.client.get(reverse('index'))

        self.assertRedirects(
            response,
            '{}?next={}'.format(reverse('login'), reverse('index')),
        )

    def test_login_without_next_redirects_to_report_list(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': self.owner.username,
                'password': 'test-password-123',
            },
        )

        self.assertRedirects(response, reverse('item_list'))

    def test_report_item_button_is_on_the_right_side_of_browse_page(self):
        response = self.client.get(reverse('item_list'))

        self.assertContains(response, 'class="report-item-button"')
        self.assertContains(response, 'Report item here')
        self.assertContains(response, 'href="{}"'.format(reverse('index')))
        self.assertNotContains(response, '>New report</a>')

    def test_community_list_can_filter_reports_by_status(self):
        resolved_item = LostAndFoundItem.objects.create(
            owner=self.owner,
            item_name='Returned backpack',
            description='Already returned to its owner.',
            category='Personal',
            location='Library',
            date_lost_found='2026-10-02',
            status='Resolved',
        )

        response = self.client.get(reverse('item_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OPEN REPORTS')
        self.assertContains(response, 'Test phone')
        self.assertNotContains(response, 'Returned backpack')
        self.assertContains(response, 'name="status"')
        self.assertEqual(list(response.context['items']), [self.item])

        open_response = self.client.get(reverse('item_list'), {'status': 'Open'})
        self.assertEqual(list(open_response.context['items']), [self.item])
        self.assertContains(open_response, 'OPEN REPORTS')
        self.assertNotContains(open_response, 'Returned backpack')

        resolved_response = self.client.get(
            reverse('item_list'),
            {'status': 'Resolved'},
        )
        self.assertEqual(list(resolved_response.context['items']), [resolved_item])
        self.assertContains(resolved_response, 'RESOLVED REPORTS')
        self.assertNotContains(resolved_response, 'Test phone')

    def test_search_button_is_between_keyword_and_status_filter(self):
        response = self.client.get(reverse('item_list'))
        html = response.content.decode()

        keyword_position = html.index('name="q"')
        search_button_position = html.index('>Search</button>')
        status_position = html.index('name="status"')

        self.assertLess(keyword_position, search_button_position)
        self.assertLess(search_button_position, status_position)

    def test_unknown_status_filter_defaults_to_open(self):
        response = self.client.get(reverse('item_list'), {'status': 'All'})

        self.assertEqual(response.context['selected_status'], 'Open')
        self.assertEqual(list(response.context['items']), [self.item])

    def test_signed_in_user_can_create_report(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('index'),
            {
                'item_name': 'Lost keys',
                'description': 'A small key ring.',
                'category': 'Accessories',
                'location': 'Student center',
                'date_lost_found': '2026-10-03',
            },
        )

        new_item = LostAndFoundItem.objects.get(item_name='Lost keys')
        self.assertEqual(new_item.owner, self.owner)
        self.assertEqual(new_item.status, 'Open')
        self.assertRedirects(response, reverse('item_detail', args=[new_item.item_id]))

    def test_other_category_is_saved_as_custom_text(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('index'),
            {
                'item_name': 'Lost sketchbook',
                'description': 'A blue cover.',
                'category': 'Other',
                'other_category': 'Art supplies',
                'location': 'Art room',
                'date_lost_found': '2026-10-03',
            },
        )

        new_item = LostAndFoundItem.objects.get(item_name='Lost sketchbook')
        self.assertEqual(new_item.category, 'Art supplies')
        self.assertRedirects(response, reverse('item_detail', args=[new_item.item_id]))

    def test_other_category_requires_custom_text(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('index'),
            {
                'item_name': 'Lost sketchbook',
                'description': 'A blue cover.',
                'category': 'Other',
                'other_category': '',
                'location': 'Art room',
                'date_lost_found': '2026-10-03',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LostAndFoundItem.objects.filter(item_name='Lost sketchbook').exists())
        self.assertContains(response, 'Enter the category for this item.')

    def test_signed_in_user_can_upload_item_image(self):
        image_content = BytesIO()
        Image.new('RGB', (20, 20), color='white').save(image_content, format='PNG')
        upload = SimpleUploadedFile(
            'lost-item.png',
            image_content.getvalue(),
            content_type='image/png',
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('index'),
            {
                'item_name': 'Lost camera',
                'description': 'Small black camera.',
                'category': 'Electronics',
                'location': 'Library',
                'date_lost_found': '2026-10-03',
                'image': upload,
            },
        )

        new_item = LostAndFoundItem.objects.get(item_name='Lost camera')
        self.assertTrue(new_item.image.name.startswith('lost_item_images/'))
        self.assertRedirects(response, reverse('item_detail', args=[new_item.item_id]))

        detail_response = self.client.get(
            reverse('item_detail', args=[new_item.item_id])
        )
        self.assertContains(detail_response, 'class="detail-layout"')
        self.assertContains(detail_response, 'class="polaroid"')
        self.assertContains(detail_response, new_item.image.url)

    def test_only_owner_can_edit_or_delete_report(self):
        self.client.force_login(self.other_user)

        edit_response = self.client.get(
            reverse('item_edit', args=[self.item.item_id])
        )
        delete_response = self.client.get(
            reverse('item_confirm_delete', args=[self.item.item_id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)

    def test_owner_can_delete_report_after_confirmation(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('item_confirm_delete', args=[self.item.item_id])
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(
            LostAndFoundItem.objects.filter(pk=self.item.item_id).exists()
        )

    def test_authenticated_user_can_comment(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('add_comment', args=[self.item.item_id]),
            {'text': 'I saw this near the library entrance.'},
        )

        comment = Comment.objects.get(item=self.item)
        self.assertEqual(comment.user, self.other_user)
        self.assertRedirects(
            response,
            reverse('item_detail', args=[self.item.item_id]),
        )

    def test_item_detail_renders_comments_and_comment_form(self):
        Comment.objects.create(
            item=self.item,
            user=self.owner,
            text='I lost this item.',
        )
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('item_detail', args=[self.item.item_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'I lost this item.')
        self.assertContains(response, 'Post comment')

    def test_resolved_report_shows_existing_comments_but_closes_comment_form(self):
        self.item.status = 'Resolved'
        self.item.save(update_fields=['status'])
        Comment.objects.create(
            item=self.item,
            user=self.owner,
            text='This existing comment remains visible.',
        )
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse('item_detail', args=[self.item.item_id])
        )

        self.assertContains(response, 'This existing comment remains visible.')
        self.assertContains(response, 'This report is resolved. Comments are closed.')
        self.assertNotContains(response, 'Post comment')

    def test_cannot_post_comment_to_resolved_report(self):
        self.item.status = 'Resolved'
        self.item.save(update_fields=['status'])
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse('add_comment', args=[self.item.item_id]),
            {'text': 'A late comment should be blocked.'},
        )

        self.assertRedirects(
            response,
            reverse('item_detail', args=[self.item.item_id]),
        )
        self.assertFalse(Comment.objects.filter(item=self.item).exists())

    def test_comment_author_can_open_edit_form(self):
        comment = Comment.objects.create(
            item=self.item,
            user=self.owner,
            text='I lost this item.',
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse('comment_edit', args=[comment.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit comment')

    def test_registration_creates_and_signs_in_user(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'new-user',
                'password1': 'Safe-test-password-456!',
                'password2': 'Safe-test-password-456!',
            },
        )

        self.assertRedirects(response, reverse('item_list'))
        self.assertTrue(
            self.client.session.get('_auth_user_id')
        )

    def test_profile_page_requires_login(self):
        response = self.client.get(reverse('profile'))

        self.assertRedirects(
            response,
            '{}?next={}'.format(reverse('login'), reverse('profile')),
        )

    def test_signed_in_user_can_view_and_update_profile(self):
        self.client.force_login(self.owner)
        profile_response = self.client.get(reverse('profile'))

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, 'ACCOUNT DETAILS')
        self.assertContains(profile_response, 'Username')

        update_response = self.client.post(
            reverse('profile'),
            {
                'username': 'owner-updated',
                'first_name': 'Robin',
                'last_name': 'Belvestre',
                'email': 'robin@example.com',
            },
        )

        self.owner.refresh_from_db()
        self.assertEqual(self.owner.username, 'owner-updated')
        self.assertEqual(self.owner.first_name, 'Robin')
        self.assertEqual(self.owner.last_name, 'Belvestre')
        self.assertEqual(self.owner.email, 'robin@example.com')
        self.assertRedirects(update_response, reverse('profile'))

    def test_only_comment_author_can_edit_or_delete_comment(self):
        comment = Comment.objects.create(
            item=self.item,
            user=self.owner,
            text='I lost this item.',
        )
        self.client.force_login(self.other_user)

        edit_response = self.client.get(
            reverse('comment_edit', args=[comment.id])
        )
        delete_response = self.client.post(
            reverse('comment_delete', args=[comment.id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(Comment.objects.filter(pk=comment.id).exists())

    def test_owner_can_mark_report_resolved(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('mark_resolved', args=[self.item.item_id])
        )

        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'Resolved')
        self.assertRedirects(
            response,
            reverse('item_detail', args=[self.item.item_id]),
        )
