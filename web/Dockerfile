FROM nginx:stable
RUN rm -f /etc/nginx/conf.d/default.conf
COPY conf.default /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/
RUN cp /usr/share/nginx/html/index.html /opt/index.html.template
ENV NODE_NAME=web-frontend-server NODE_LABEL="Node 1"
RUN printf '%s\n' '#!/bin/sh' 'set -eu' \
    'envsubst '\''${NODE_NAME} ${NODE_LABEL}'\'' < /opt/index.html.template > /usr/share/nginx/html/index.html' \
    > /docker-entrypoint.d/40-render-node.sh \
    && chmod +x /docker-entrypoint.d/40-render-node.sh
RUN chmod -R 755 /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]