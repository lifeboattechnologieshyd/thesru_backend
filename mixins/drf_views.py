import logging

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response

logger = logging.getLogger("default")


########################
#    CUSTOM RESPONSE   #
########################


class CustomResponse:
    @staticmethod
    def get_custom_response_serializer(serializer_class, many=True):
        class CustomResponseSerializer(serializers.Serializer):
            success = serializers.BooleanField()
            errorCode = serializers.IntegerField()
            description = serializers.CharField()
            total = serializers.IntegerField()
            info = serializer_class(many=many)

        return CustomResponseSerializer

    @staticmethod
    def successResponse(
        data, errorCode=0, description="Request Successful", total=0, status=status.HTTP_200_OK, **kwargs
    ):
        return Response(
            {
                "success": True,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                **kwargs,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def errorResponse(
        data=None,
        errorCode=0,
        description="Request Failed",
        total=0,
        status=status.HTTP_200_OK,
        **kwargs,
    ):
        if data is None:
            data = {}
        return Response(
            {
                "success": False,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                "data": data,
                **kwargs,
            },
            status=status,
        )


########################################
#   GENERICS OVERRIDES FOR DRF VIEWS   #
########################################


######################
# LIST & CREATE VIEW #
######################


class CustomListCreateAPIView(ListCreateAPIView, CustomResponse):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            total = self.paginator.page.paginator.count  # Pagination count
            return self.successResponse(data=serializer.data, total=total)
        serializer = self.get_serializer(queryset, many=True)
        return self.successResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return self.successResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        except Exception as error:
            logger.exception(f"Unknown error in list create api: {str(error)}")
            return self.errorResponse(data=serializer.errors, description=str(error))


#####################
#    CREATE VIEW    #
#####################


class CustomCreateAPIView(CreateAPIView, CustomResponse):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return self.successResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        else:
            return self.errorResponse(data=serializer.errors)


#####################
#    LIST VIEW    #
#####################
class CustomLISTAPIView(ListAPIView, CustomResponse):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            total = self.paginator.page.paginator.count  # Pagination count
            return self.successResponse(data=serializer.data, total=total)
        serializer = self.get_serializer(queryset, many=True)
        return self.successResponse(data=serializer.data)


#######################
#    RETRIEVE VIEW    #
#######################


class CustomRetrieveAPIView(RetrieveAPIView, CustomResponse):
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.successResponse(data=serializer.data)


#######################
#    UPDATE VIEW    #
#######################


class CustomUpdateAPIView(UpdateAPIView, CustomResponse):
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return self.errorResponse(data=serializer.errors)

        try:
            self.perform_update(serializer)
            return self.successResponse(data=serializer.data)
        except ValidationError:
            return self.errorResponse(data=serializer.errors)
        except Exception as error:
            logger.exception(f"Unknown error in update api: {str(error)}")
            return self.errorResponse(data=str(error), description="Something went wrong")


############################################
#      RETRIEVE, UPDATE & DESTROY VIEW     #
############################################


class CustomRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView, CustomResponse):
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.successResponse(data=serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return self.errorResponse(data=serializer.errors)

        try:
            self.perform_update(serializer)
            return self.successResponse(data=serializer.data)
        except ValidationError:
            return self.errorResponse(data=serializer.errors)
        except Exception as error:
            logger.exception(f"Unknown error in update api: {str(error)}")
            return self.errorResponse(data=str(error), description="Something went wrong")

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # Get the object to be deleted
            self.perform_destroy(instance)  # Perform the deletion
            return self.successResponse(data={"message": "Deleted successfully"})  # Respond with success

        except Exception as error:
            logger.exception(f"Unknown error in destroy API: {str(error)}")
            return self.errorResponse(
                data={"error": str(error)},
                description="Failed to delete the resource.",
            )
