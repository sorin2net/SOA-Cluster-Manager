import logging
from concurrent import futures

import grpc

import idm_pb2_grpc
from config import load_config
from service import IdentityService
from tokens import TokenManager
from users_repository import UserRepository


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config()

    users = UserRepository(config.db_host, config.db_port, config.db_name, config.db_user, config.db_password)
    tokens = TokenManager(config.jwt_secret, config.jwt_issuer, config.token_ttl_seconds)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    idm_pb2_grpc.add_IdentityServiceServicer_to_server(IdentityService(users, tokens), server)
    server.add_insecure_port(f"[::]:{config.grpc_port}")
    server.start()
    logging.info("Serviciul IDM asculta pe portul %d", config.grpc_port)

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Oprire serviciu IDM")
        server.stop(grace=2)


if __name__ == "__main__":
    main()
