def feedback(request):
    """Feedback form view"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'terminology/feedback_success.html')
    else:
        form = FeedbackForm()
    return render(request, 'terminology/feedback.html', {'form': form})
