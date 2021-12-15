This is a collection of Automated Market Takers designed to egress markets across all of Paradigm's products. They are first and foremost QA tools as opposed to systems examples, etc.

The AMTs use a combination of *RESToverHTTP* requests and *JSON-RPCoverWebSocket* channels to step through common Taker workflows and send a consistent stream of Quotes/Orders.

You can run each product either by building the docker image and running it as a docker service or you can just update the values in the respective `auto-taker.py` file and run/debug.

All AMTs have been written using **Python 3.9**.

## Supported Products:

* FSPD

<!-- CONTACT -->
## Contact

Elliot Parker 
* Telegram: [@ElliotPark](https://t.me/ElliotPark)

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/elliot-parker-3454a4167/