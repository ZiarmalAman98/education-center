def language(request):
    """Expose the selected interface language to every template."""
    selected = request.session.get('language', 'ps')
    return {'interface_language': selected, 'is_english': selected == 'en'}
