from flask import Flask, render_template

app = Flask(__name__)

@app.route('/prize')
def prize_page():
    return render_template('prize.html', content=(
        'NotifyNL heeft geen verdienmodel op basis van het aantal berichten dat je verstuurt.\n\n'
        'We belasten kosten door voor:\n'
        '- het hosten van de service\n'
        '- de brieven die u verstuurt\n'
        '- de sms berichten die u verstuurt\n\n'
        'U kunt een servicelevel afnemen, en deelnemen in de community van afnemers die samen het code stewardship van NotifyNL betalen.'
    ))