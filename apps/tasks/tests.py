from starlette import status
from customers.tests.customer import CustomAPITestCase


class UserTaskAPITestCase(CustomAPITestCase):
    def test_task_list(self):
        self.logout()
        self.login(username='custo1')
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_list_from_admin_user(self):
        self.logout()
        self.login(username='custo1')
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_link_unauth(self):
        self.logout()
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
