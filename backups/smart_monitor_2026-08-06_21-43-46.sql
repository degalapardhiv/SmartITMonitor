--
-- PostgreSQL database dump
--

\restrict RIhesLzk9kPSDt1FwnB7eGYHoSk2eJrYX58n1qTeZAYftzFemdQnbaZarhY6Cll

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: smartadmin
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    device_id integer,
    hostname character varying,
    alert_type character varying,
    value double precision,
    message character varying,
    severity character varying,
    created_at timestamp without time zone
);


ALTER TABLE public.alerts OWNER TO smartadmin;

--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: smartadmin
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerts_id_seq OWNER TO smartadmin;

--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: smartadmin
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- Name: device_metrics; Type: TABLE; Schema: public; Owner: smartadmin
--

CREATE TABLE public.device_metrics (
    id integer NOT NULL,
    device_id integer NOT NULL,
    cpu double precision NOT NULL,
    ram double precision NOT NULL,
    disk double precision NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.device_metrics OWNER TO smartadmin;

--
-- Name: device_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: smartadmin
--

CREATE SEQUENCE public.device_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.device_metrics_id_seq OWNER TO smartadmin;

--
-- Name: device_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: smartadmin
--

ALTER SEQUENCE public.device_metrics_id_seq OWNED BY public.device_metrics.id;


--
-- Name: devices; Type: TABLE; Schema: public; Owner: smartadmin
--

CREATE TABLE public.devices (
    id integer NOT NULL,
    hostname character varying,
    ip character varying,
    cpu double precision,
    ram double precision,
    disk double precision,
    status character varying,
    department character varying,
    lab character varying,
    location character varying,
    os character varying,
    last_seen timestamp without time zone
);


ALTER TABLE public.devices OWNER TO smartadmin;

--
-- Name: devices_id_seq; Type: SEQUENCE; Schema: public; Owner: smartadmin
--

CREATE SEQUENCE public.devices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.devices_id_seq OWNER TO smartadmin;

--
-- Name: devices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: smartadmin
--

ALTER SEQUENCE public.devices_id_seq OWNED BY public.devices.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: smartadmin
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying NOT NULL,
    password_hash character varying NOT NULL,
    role character varying NOT NULL
);


ALTER TABLE public.users OWNER TO smartadmin;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: smartadmin
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO smartadmin;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: smartadmin
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- Name: device_metrics id; Type: DEFAULT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.device_metrics ALTER COLUMN id SET DEFAULT nextval('public.device_metrics_id_seq'::regclass);


--
-- Name: devices id; Type: DEFAULT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.devices ALTER COLUMN id SET DEFAULT nextval('public.devices_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: smartadmin
--

COPY public.alerts (id, device_id, hostname, alert_type, value, message, severity, created_at) FROM stdin;
\.


--
-- Data for Name: device_metrics; Type: TABLE DATA; Schema: public; Owner: smartadmin
--

COPY public.device_metrics (id, device_id, cpu, ram, disk, created_at) FROM stdin;
1	1	7.4	67.3	6	2026-08-06 15:46:40.353694
2	1	5	68.4	6	2026-08-06 15:47:11.46056
3	1	9.9	67.6	6	2026-08-06 15:47:42.588296
4	1	5.5	69.2	6	2026-08-06 15:48:13.687488
5	1	7.8	67.7	6	2026-08-06 15:48:44.771009
6	1	9.4	67.6	6	2026-08-06 15:49:15.828824
7	1	5.8	68.1	6	2026-08-06 15:49:46.998749
8	1	8.3	66.9	6	2026-08-06 15:50:17.804368
9	1	6.1	66.6	6	2026-08-06 15:50:48.990482
10	1	4.2	69.2	6	2026-08-06 15:51:20.069943
11	1	6.9	67.9	6.1	2026-08-06 15:51:51.196904
12	1	8.4	67.6	6.1	2026-08-06 15:52:22.520062
13	1	8.2	67.6	6.1	2026-08-06 15:52:53.642045
14	1	4.1	68.2	6.1	2026-08-06 15:53:24.806238
15	1	3.5	67.4	6.1	2026-08-06 15:53:56.154034
16	1	4.1	67.6	6.1	2026-08-06 15:54:27.46739
17	1	11.8	67.9	6.1	2026-08-06 15:54:58.620925
18	1	3.3	67.3	6.1	2026-08-06 15:55:29.739425
19	1	8.8	67	6.1	2026-08-06 15:56:00.90184
20	1	4.4	67	6.1	2026-08-06 15:56:31.979743
21	1	7.7	67.5	6.1	2026-08-06 15:57:03.04597
22	1	8.8	68.3	6.1	2026-08-06 15:57:34.113092
23	1	9.2	70.1	6.1	2026-08-06 15:58:05.716262
24	1	3.8	66.4	6.1	2026-08-06 15:58:36.91402
25	1	10.5	67.9	6.1	2026-08-06 15:59:08.119838
26	1	11.6	65.9	6.1	2026-08-06 15:59:39.312006
27	1	8.2	67.7	6.1	2026-08-06 16:00:10.429384
28	1	2.5	66.3	6.1	2026-08-06 16:00:41.517245
29	1	3.4	65.3	6.1	2026-08-06 16:01:12.598032
30	1	5.2	66.3	6.1	2026-08-06 16:01:43.694158
31	1	5.1	67.2	6.1	2026-08-06 16:02:14.773179
32	1	6.2	66.8	6.2	2026-08-06 16:02:45.941354
33	1	11.3	67	6.2	2026-08-06 16:03:17.250281
34	1	11.7	67.5	6.2	2026-08-06 16:03:48.315595
35	1	6	66.8	6.2	2026-08-06 16:04:19.399958
36	1	5.6	66.8	6.2	2026-08-06 16:04:50.470477
37	1	3.6	66.4	6.2	2026-08-06 16:06:23.796704
38	1	3.6	66.2	6.2	2026-08-06 16:06:54.941878
39	1	3.2	66.3	6.2	2026-08-06 16:07:26.0302
40	1	6.3	67.1	6.2	2026-08-06 16:07:57.205331
41	1	1.9	66.4	6.2	2026-08-06 16:08:28.272693
42	1	3.3	66.3	6.2	2026-08-06 16:08:59.352183
43	1	10.3	67.9	6.2	2026-08-06 16:09:30.427
44	1	6	68.2	6.2	2026-08-06 16:11:03.52393
45	1	6.7	69.1	6.2	2026-08-06 16:11:34.621448
46	1	3.9	67.7	6.2	2026-08-06 16:12:05.699964
47	1	5.5	68.1	6.2	2026-08-06 16:13:07.817146
48	1	5.6	69.2	6.2	2026-08-06 16:13:38.918328
\.


--
-- Data for Name: devices; Type: TABLE DATA; Schema: public; Owner: smartadmin
--

COPY public.devices (id, hostname, ip, cpu, ram, disk, status, department, lab, location, os, last_seen) FROM stdin;
1	kali	10.234.69.225	5.6	69.2	6.2	Online	Computer Science & Engineering	Cyber Security Lab	Block A	Linux 7.0.12+kali-amd64	2026-08-06 15:46:40.286883
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: smartadmin
--

COPY public.users (id, username, password_hash, role) FROM stdin;
\.


--
-- Name: alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: smartadmin
--

SELECT pg_catalog.setval('public.alerts_id_seq', 1, false);


--
-- Name: device_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: smartadmin
--

SELECT pg_catalog.setval('public.device_metrics_id_seq', 48, true);


--
-- Name: devices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: smartadmin
--

SELECT pg_catalog.setval('public.devices_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: smartadmin
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: device_metrics device_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.device_metrics
    ADD CONSTRAINT device_metrics_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_alerts_id; Type: INDEX; Schema: public; Owner: smartadmin
--

CREATE INDEX ix_alerts_id ON public.alerts USING btree (id);


--
-- Name: ix_device_metrics_id; Type: INDEX; Schema: public; Owner: smartadmin
--

CREATE INDEX ix_device_metrics_id ON public.device_metrics USING btree (id);


--
-- Name: ix_devices_hostname; Type: INDEX; Schema: public; Owner: smartadmin
--

CREATE UNIQUE INDEX ix_devices_hostname ON public.devices USING btree (hostname);


--
-- Name: ix_devices_id; Type: INDEX; Schema: public; Owner: smartadmin
--

CREATE INDEX ix_devices_id ON public.devices USING btree (id);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: smartadmin
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: device_metrics device_metrics_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: smartadmin
--

ALTER TABLE ONLY public.device_metrics
    ADD CONSTRAINT device_metrics_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict RIhesLzk9kPSDt1FwnB7eGYHoSk2eJrYX58n1qTeZAYftzFemdQnbaZarhY6Cll

