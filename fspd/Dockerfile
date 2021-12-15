FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1
ENV PARADIGM_ENVIRONMENT="TEST"
ENV LOGGING_LEVEL="INFO"
ENV PARADIGM_TAKER_ACCOUNT_NAME="<venue-api-key-name-on-paradigm>"
ENV PARADIGM_TAKER_ACCESS_KEY="<access-key>"
ENV PARADIGM_TAKER_SECRET_KEY="<secret-key>"
ENV ORDER_NUMBER_PER_STRATEGY='1'
ENV ORDER_SUBMISSION_LOWER_BOUNDARY='1'
ENV ORDER_SUBMISSION_HIGHER_BOUNDARY='2'

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY auto-taker.py /

CMD ["sh", "-c", "python /auto-taker.py $PARADIGM_ENVIRONMENT \
                                        $LOGGING_LEVEL \
                                        $PARADIGM_TAKER_ACCOUNT_NAME \
                                        $PARADIGM_TAKER_ACCESS_KEY \
                                        $PARADIGM_TAKER_SECRET_KEY \
                                        $ORDER_NUMBER_PER_STRATEGY \
                                        $ORDER_SUBMISSION_LOWER_BOUNDARY \
                                        $ORDER_SUBMISSION_HIGHER_BOUNDARY"]