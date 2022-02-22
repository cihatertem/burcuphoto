def project_directory_path(instance, filename):
    return 'projects/{0}/{1}'.format(instance.slug, filename)


def portfolio_directory_path(instance, filename):
    return 'projects/{0}/photos/{1}'.format(instance.project.slug, filename)
