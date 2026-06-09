from predictions.models import WinnerPrediction


def winner_prediction_status(request):
    if not request.user.is_authenticated:
        return {}
    has_winner_prediction = WinnerPrediction.objects.filter(user_id=request.user).exists()
    return {'has_winner_prediction': has_winner_prediction}
