def test_prize_page(client):
    response = client.get('/prize')

    assert b"NotifyNL heeft geen verdienmodel op basis van het aantal berichten" in response.data
    assert b"het hosten van de service" in response.data
    assert b"de brieven die u verstuurt" in response.data
    assert b"de sms berichten die u verstuurt" in response.data
    assert b"code stewardship van NotifyNL betalen" in response.data