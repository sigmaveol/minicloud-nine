# A Dockerfile is a text file containing instructions for building a Docker image.

# start with an existing Nginx image
FROM nginx:stable 

# Remove the default Nginx website configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy our customized Nginx configuration into the image
COPY conf.default /etc/nginx/conf.d/default.conf
# copy the website HTML files into the image
COPY html/ /usr/share/nginx/html/

# Document the container uses port 80
EXPOSE 80

# Start Nginx in the foreground when the container runs
CMD ["nginx", "-g", "daemon off;"]  

# This file is use when we executed: docker compose build web-frontend-server 