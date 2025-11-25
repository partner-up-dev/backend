if __name__ == "__main__":
    print(R"""

        |     |     =     |————\    |—————\   |—————     =     |\     /|
        |     |   =   =   |    —\   |     |   |        =   =   | \   / |
        |—————|  = = = =  |     —|  |—————/   |—————  = = = =  |  \ /  |
        |     |  =     =  |    —/   |    |    |       =     =  |   |   |
        |     |  =     =  |————/    |     \   |—————  =     =  |       |


                    #######################################
                            Anana-Backend-Main
                        --Powered by BlueFirmament--
        
                    2025(c) all copyrights reserved
                    #######################################


    [LOG OUTPUT]:
    """)

    # Load environment variables first
    import env_loader

    import settings.auth
    from blue_firmament.session.common import CommonSession

    CommonSession.ACCESS_TOKEN_PAYLOAD_ID_CLAIM = "session_id"

    from blue_firmament.log import get_logger

    LOGGER = get_logger(__name__)

    from blue_firmament.core.app import BlueFirmamentApp

    app = BlueFirmamentApp(name="PartnerUpMain")

    # [transport]
    from blue_firmament.transport.http import HTTPTransporter
    from blue_firmament.transport.pubsub import PubSubTransporter

    from settings.transport import get_setting as get_transport_setting

    app.add_transporter(
        HTTPTransporter(
            app,
            get_transport_setting().http_host,
            get_transport_setting().http_port,
        )
    )

    from dal import DefaultRedis

    app.add_transporter(PubSubTransporter(app, DefaultRedis(), "events", name="event"))

    from blue_firmament import event

    event.EVENT_BROKER = DefaultRedis(channel_name="events")

    # [managers]
    from communication.managers.chat import ChatManager
    from communication.managers.message import BaseMessageManager, PlainMessageManager
    from communication.managers.message.approval import ApprovalMessageManager
    from main.managers.partner_request import BasePRManager, PartnerManager
    from main.managers.partner_request.application import PartnerApplicationManager
    from main.managers.partner_request.trip.commute import CommutePRManager
    from main.managers.partner_request.trip.ride_hailing import RideHailingPRManager
    from main.managers.payment import wechat  # for activation
    from main.managers.split_bill import SplitBillManager
    from main.managers.split_bill.contribution import ContributionManager
    from main.managers.base.route import LocationManager

    app.add_managers(
        BasePRManager,
        PartnerManager,
        PartnerApplicationManager,
        RideHailingPRManager,
        CommutePRManager,
        ChatManager,
        BaseMessageManager,
        PlainMessageManager,
        ApprovalMessageManager,
        SplitBillManager,
        ContributionManager,
        LocationManager,
    )

    app.run()
