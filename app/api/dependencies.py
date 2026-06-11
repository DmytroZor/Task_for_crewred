from typing import Annotated

from fastapi import Depends, Request

from app.services.art_institute import ArtInstituteClient


def get_art_client(request: Request) -> ArtInstituteClient:
    return request.app.state.art_client


ArtClient = Annotated[ArtInstituteClient, Depends(get_art_client)]
