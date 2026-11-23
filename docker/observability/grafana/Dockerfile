FROM grafana/grafana:13.3.1

# El plugin se fija por version en build: GF_INSTALL_PLUGINS no permite
# fijar version, y el ADR (D4) exige una version concreta. Si el runtime no
# puede fijarla, se hornea: esto es eso.
#
# Se instala fuera de /var/lib/grafana a proposito: ese path se monta desde
# ${DATA_DIR}/grafana en runtime y taparia el plugin horneado.
ARG ZABBIX_PLUGIN_VERSION=6.10.3
ARG INFINITY_PLUGIN_VERSION=4.1.8
ARG PLUGIN_DIR=/opt/grafana-plugins

USER root

RUN grafana cli --pluginsDir "${PLUGIN_DIR}" \
      plugins install alexanderzobnin-zabbix-app "${ZABBIX_PLUGIN_VERSION}" \
 && grafana cli --pluginsDir "${PLUGIN_DIR}" \
      plugins install yesoreyeram-infinity-datasource "${INFINITY_PLUGIN_VERSION}" \
 && chown -R 472:0 "${PLUGIN_DIR}"

USER grafana
