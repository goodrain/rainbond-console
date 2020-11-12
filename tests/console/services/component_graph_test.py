from console.services.app_config.component_graph import ComponentGraphService


def test_add_or_update_label():
    component_graph_service = ComponentGraphService()
    promsql = component_graph_service.add_or_update_label(
        "foobar", "container_memory_rss{name=~\"k8s_1aa695008a85f6aacf3b9ed6342279c5.*\"}/1024/1024")
    want = "container_memory_rss{name=~\"k8s_1aa695008a85f6aacf3b9ed6342279c5.*\",service_id=\"foobar\"} / 1024 / 1024"
    assert promsql == want
