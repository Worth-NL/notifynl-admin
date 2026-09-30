from app import organisations_client
from tests.utils import RedisClientMock

LETTER_PROVIDER = {"identifier": "pingen", "address_placement": "60mm"}


def test_get_organisation_letter_provider(notify_admin, mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.organisations_api_client.OrganisationsClient.get", return_value={"data": LETTER_PROVIDER}
    )

    assert organisations_client.get_organisation_letter_provider(fake_uuid) == LETTER_PROVIDER
    mock_get.assert_called_once_with(url=f"/organisations/{fake_uuid}/letter-provider")


def test_set_organisation_letter_provider_clears_the_cached_services(notify_admin, mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_post = mocker.patch(
        "app.notify_client.organisations_api_client.OrganisationsClient.post", return_value={"data": LETTER_PROVIDER}
    )
    data = {"provider": "pingen", "updated_by_id": fake_uuid}

    assert (
        organisations_client.set_organisation_letter_provider(fake_uuid, data, cached_service_ids=["a", "b"])
        == LETTER_PROVIDER
    )

    mock_post.assert_called_once_with(url=f"/organisations/{fake_uuid}/letter-provider", data=data)
    mock_redis_delete.assert_called_with_args("service-a", "service-b")


def test_set_organisation_letter_provider_without_services(notify_admin, mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mocker.patch(
        "app.notify_client.organisations_api_client.OrganisationsClient.post", return_value={"data": LETTER_PROVIDER}
    )

    organisations_client.set_organisation_letter_provider(fake_uuid, {"provider": "pingen"}, cached_service_ids=[])

    mock_redis_delete.assert_not_called()
