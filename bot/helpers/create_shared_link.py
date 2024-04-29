import dropbox

def create_shared_link(dbx, dropbox_path):
    """Create a shared link for the given path in Dropbox.

    :param dbx: Dropbox instance.
    :param dropbox_path: The Dropbox path to create a shared link for.
    :return: URL of the shared link.
    """
    link_settings = dropbox.sharing.SharedLinkSettings(
        requested_visibility=dropbox.sharing.RequestedVisibility.public,
        audience=dropbox.sharing.LinkAudience.public
    )

    try:
        # Attempt to create a new shared link
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path, link_settings)
        return shared_link_metadata.url
    except dropbox.exceptions.ApiError as e:
        if e.error.is_shared_link_already_exists():
            # If the shared link already exists, retrieve and return it
            shared_links = dbx.sharing_list_shared_links(dropbox_path).links
            if shared_links:
                return shared_links[0].url
        else:
            raise