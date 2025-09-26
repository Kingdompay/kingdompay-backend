--
-- PostgreSQL database dump
--

\restrict v7Tkwrg2sr0bmu6r90vZCAmqupYo8Cvhi3LxhiSMpcT3LnP5hnrHWtdD0qbY8Uv

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 15.14

-- Started on 2025-09-26 21:56:42 UTC

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

--
-- TOC entry 5 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- TOC entry 3602 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 284 (class 1255 OID 24607)
-- Name: add_transaction(integer, integer, character varying, numeric, text); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.add_transaction(p_source_wallet_id integer, p_destination_wallet_id integer, p_type character varying, p_amount numeric, p_description text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_source_balance NUMERIC(15,2);
    new_destination_balance NUMERIC(15,2);
BEGIN
    
    PERFORM pg_advisory_xact_lock(1);  

    -- Deposit
    IF p_type = 'DEPOSIT' THEN
        UPDATE wallets
        SET balance = balance + p_amount, updated_at = now()
        WHERE id = p_destination_wallet_id
        RETURNING balance INTO new_destination_balance;

        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, destination_balance_after, description, status
        )
        VALUES (NULL, p_destination_wallet_id, 'DEPOSIT',
            p_amount, new_destination_balance, p_description, 'SUCCESS');

    -- Withdrawal
    ELSIF p_type = 'WITHDRAWAL' THEN
        UPDATE wallets
        SET balance = balance - p_amount, updated_at = now()
        WHERE id = p_source_wallet_id AND balance >= p_amount
        RETURNING balance INTO new_source_balance;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Insufficient funds in wallet %', p_source_wallet_id;
        END IF;

        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, source_balance_after, description, status
        )
        VALUES (p_source_wallet_id, NULL, 'WITHDRAWAL',
            p_amount, new_source_balance, p_description, 'SUCCESS');

    -- Transfer / Payment
    ELSIF p_type IN ('TRANSFER', 'PAYMENT') THEN
        -- Debit sender
        UPDATE wallets
        SET balance = balance - p_amount, updated_at = now()
        WHERE id = p_source_wallet_id AND balance >= p_amount
        RETURNING balance INTO new_source_balance;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Insufficient funds in wallet %', p_source_wallet_id;
        END IF;

        -- Credit receiver
        UPDATE wallets
        SET balance = balance + p_amount, updated_at = now()
        WHERE id = p_destination_wallet_id
        RETURNING balance INTO new_destination_balance;

        -- Log transaction
        INSERT INTO transactions (
            source_wallet_id, destination_wallet_id, transaction_type,
            amount, source_balance_after, destination_balance_after, description, status
        )
        VALUES (p_source_wallet_id, p_destination_wallet_id, p_type,
            p_amount, new_source_balance, new_destination_balance, p_description, 'SUCCESS');

    ELSE
        RAISE EXCEPTION 'Invalid transaction type: %', p_type;
    END IF;
END;
$$;


ALTER FUNCTION public.add_transaction(p_source_wallet_id integer, p_destination_wallet_id integer, p_type character varying, p_amount numeric, p_description text) OWNER TO admin;

--
-- TOC entry 271 (class 1255 OID 16488)
-- Name: create_wallet_for_user(); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.create_wallet_for_user() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO wallets (user_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.create_wallet_for_user() OWNER TO admin;

--
-- TOC entry 272 (class 1255 OID 16490)
-- Name: update_wallet_timestamp(); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.update_wallet_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_wallet_timestamp() OWNER TO admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 32770)
-- Name: communities; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.communities (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(50) NOT NULL,
    parent_id integer,
    description text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT communities_type_check CHECK (((type)::text = ANY ((ARRAY['State Nation'::character varying, 'Natural Nation'::character varying, 'Ethnic Community'::character varying, 'Religious Community'::character varying, 'Organization'::character varying, 'Institution'::character varying, 'Company'::character varying, 'Village'::character varying, 'Clan'::character varying, 'Family'::character varying])::text[])))
);


ALTER TABLE public.communities OWNER TO admin;

--
-- TOC entry 221 (class 1259 OID 32769)
-- Name: communities_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.communities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.communities_id_seq OWNER TO admin;

--
-- TOC entry 3603 (class 0 OID 0)
-- Dependencies: 221
-- Name: communities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.communities_id_seq OWNED BY public.communities.id;


--
-- TOC entry 228 (class 1259 OID 32827)
-- Name: community_contributions; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.community_contributions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    community_id integer NOT NULL,
    amount numeric(18,2) NOT NULL,
    currency character varying(10) DEFAULT 'KSH'::character varying,
    contributed_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    reference text
);


ALTER TABLE public.community_contributions OWNER TO admin;

--
-- TOC entry 227 (class 1259 OID 32826)
-- Name: community_contributions_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.community_contributions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_contributions_id_seq OWNER TO admin;

--
-- TOC entry 3604 (class 0 OID 0)
-- Dependencies: 227
-- Name: community_contributions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.community_contributions_id_seq OWNED BY public.community_contributions.id;


--
-- TOC entry 230 (class 1259 OID 32848)
-- Name: community_projects; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.community_projects (
    id integer NOT NULL,
    community_id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    goal_amount numeric(18,2),
    created_by integer NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_projects_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.community_projects OWNER TO admin;

--
-- TOC entry 229 (class 1259 OID 32847)
-- Name: community_projects_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.community_projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_projects_id_seq OWNER TO admin;

--
-- TOC entry 3605 (class 0 OID 0)
-- Dependencies: 229
-- Name: community_projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.community_projects_id_seq OWNED BY public.community_projects.id;


--
-- TOC entry 232 (class 1259 OID 32870)
-- Name: community_votes; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.community_votes (
    id integer NOT NULL,
    community_id integer NOT NULL,
    project_id integer,
    created_by integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    status character varying(50) DEFAULT 'open'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT community_votes_status_check CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'closed'::character varying])::text[])))
);


ALTER TABLE public.community_votes OWNER TO admin;

--
-- TOC entry 231 (class 1259 OID 32869)
-- Name: community_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.community_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_votes_id_seq OWNER TO admin;

--
-- TOC entry 3606 (class 0 OID 0)
-- Dependencies: 231
-- Name: community_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.community_votes_id_seq OWNED BY public.community_votes.id;


--
-- TOC entry 226 (class 1259 OID 32808)
-- Name: community_wallets; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.community_wallets (
    id integer NOT NULL,
    community_id integer NOT NULL,
    wallet_id integer NOT NULL
);


ALTER TABLE public.community_wallets OWNER TO admin;

--
-- TOC entry 225 (class 1259 OID 32807)
-- Name: community_wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.community_wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.community_wallets_id_seq OWNER TO admin;

--
-- TOC entry 3607 (class 0 OID 0)
-- Dependencies: 225
-- Name: community_wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.community_wallets_id_seq OWNED BY public.community_wallets.id;


--
-- TOC entry 220 (class 1259 OID 24578)
-- Name: transactions; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    source_wallet_id integer,
    destination_wallet_id integer,
    transaction_type character varying(20) NOT NULL,
    amount numeric(15,2) NOT NULL,
    source_balance_after numeric(15,2),
    destination_balance_after numeric(15,2),
    reference_number character varying(30) DEFAULT concat('TX-', (floor((random() * ('1000000000000'::bigint)::double precision)))::bigint),
    status character varying(20) DEFAULT 'SUCCESS'::character varying NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT transactions_amount_check CHECK ((amount > (0)::numeric)),
    CONSTRAINT transactions_status_check CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'SUCCESS'::character varying, 'FAILED'::character varying])::text[]))),
    CONSTRAINT transactions_transaction_type_check CHECK (((transaction_type)::text = ANY ((ARRAY['DEPOSIT'::character varying, 'WITHDRAWAL'::character varying, 'TRANSFER'::character varying, 'PAYMENT'::character varying])::text[])))
);


ALTER TABLE public.transactions OWNER TO admin;

--
-- TOC entry 219 (class 1259 OID 24577)
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transactions_id_seq OWNER TO admin;

--
-- TOC entry 3608 (class 0 OID 0)
-- Dependencies: 219
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- TOC entry 224 (class 1259 OID 32786)
-- Name: user_communities; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.user_communities (
    id integer NOT NULL,
    user_id integer NOT NULL,
    community_id integer NOT NULL,
    role character varying(50) DEFAULT 'member'::character varying NOT NULL,
    joined_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_communities_role_check CHECK (((role)::text = ANY ((ARRAY['member'::character varying, 'leader'::character varying, 'treasurer'::character varying, 'auditor'::character varying])::text[])))
);


ALTER TABLE public.user_communities OWNER TO admin;

--
-- TOC entry 223 (class 1259 OID 32785)
-- Name: user_communities_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.user_communities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_communities_id_seq OWNER TO admin;

--
-- TOC entry 3609 (class 0 OID 0)
-- Dependencies: 223
-- Name: user_communities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.user_communities_id_seq OWNED BY public.user_communities.id;


--
-- TOC entry 216 (class 1259 OID 16402)
-- Name: users; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.users (
    id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    password character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    phone_number character varying(20) NOT NULL,
    is_phone_verified boolean DEFAULT false,
    last_login timestamp with time zone,
    updated_at timestamp with time zone,
    reset_token character varying(255),
    reset_token_expires timestamp with time zone,
    is_active boolean DEFAULT true
);


ALTER TABLE public.users OWNER TO admin;

--
-- TOC entry 215 (class 1259 OID 16401)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO admin;

--
-- TOC entry 3610 (class 0 OID 0)
-- Dependencies: 215
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 234 (class 1259 OID 32897)
-- Name: vote_casts; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.vote_casts (
    id integer NOT NULL,
    vote_id integer NOT NULL,
    user_id integer NOT NULL,
    choice character varying(50) NOT NULL,
    voted_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT vote_casts_choice_check CHECK (((choice)::text = ANY ((ARRAY['yes'::character varying, 'no'::character varying, 'abstain'::character varying])::text[])))
);


ALTER TABLE public.vote_casts OWNER TO admin;

--
-- TOC entry 233 (class 1259 OID 32896)
-- Name: vote_casts_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.vote_casts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.vote_casts_id_seq OWNER TO admin;

--
-- TOC entry 3611 (class 0 OID 0)
-- Dependencies: 233
-- Name: vote_casts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.vote_casts_id_seq OWNED BY public.vote_casts.id;


--
-- TOC entry 218 (class 1259 OID 16465)
-- Name: wallets; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.wallets (
    id integer NOT NULL,
    user_id integer NOT NULL,
    wallet_number uuid DEFAULT gen_random_uuid(),
    balance numeric(15,2) DEFAULT 0.00 NOT NULL,
    currency character varying(3) DEFAULT 'KES'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    display_number character varying(20) DEFAULT concat('WAL-', (floor((random() * (1000000000)::double precision)))::bigint),
    CONSTRAINT wallets_balance_check CHECK ((balance >= (0)::numeric)),
    CONSTRAINT wallets_currency_check CHECK (((currency)::text = ANY ((ARRAY['KES'::character varying, 'USD'::character varying, 'EUR'::character varying])::text[])))
);


ALTER TABLE public.wallets OWNER TO admin;

--
-- TOC entry 217 (class 1259 OID 16464)
-- Name: wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.wallets_id_seq OWNER TO admin;

--
-- TOC entry 3612 (class 0 OID 0)
-- Dependencies: 217
-- Name: wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.wallets_id_seq OWNED BY public.wallets.id;


--
-- TOC entry 3363 (class 2604 OID 32773)
-- Name: communities id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.communities ALTER COLUMN id SET DEFAULT nextval('public.communities_id_seq'::regclass);


--
-- TOC entry 3369 (class 2604 OID 32830)
-- Name: community_contributions id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_contributions ALTER COLUMN id SET DEFAULT nextval('public.community_contributions_id_seq'::regclass);


--
-- TOC entry 3372 (class 2604 OID 32851)
-- Name: community_projects id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_projects ALTER COLUMN id SET DEFAULT nextval('public.community_projects_id_seq'::regclass);


--
-- TOC entry 3375 (class 2604 OID 32873)
-- Name: community_votes id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_votes ALTER COLUMN id SET DEFAULT nextval('public.community_votes_id_seq'::regclass);


--
-- TOC entry 3368 (class 2604 OID 32811)
-- Name: community_wallets id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_wallets ALTER COLUMN id SET DEFAULT nextval('public.community_wallets_id_seq'::regclass);


--
-- TOC entry 3359 (class 2604 OID 24581)
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- TOC entry 3365 (class 2604 OID 32789)
-- Name: user_communities id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_communities ALTER COLUMN id SET DEFAULT nextval('public.user_communities_id_seq'::regclass);


--
-- TOC entry 3348 (class 2604 OID 16405)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 3378 (class 2604 OID 32900)
-- Name: vote_casts id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vote_casts ALTER COLUMN id SET DEFAULT nextval('public.vote_casts_id_seq'::regclass);


--
-- TOC entry 3352 (class 2604 OID 16468)
-- Name: wallets id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets ALTER COLUMN id SET DEFAULT nextval('public.wallets_id_seq'::regclass);


--
-- TOC entry 3417 (class 2606 OID 32779)
-- Name: communities communities_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.communities
    ADD CONSTRAINT communities_pkey PRIMARY KEY (id);


--
-- TOC entry 3427 (class 2606 OID 32836)
-- Name: community_contributions community_contributions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_contributions
    ADD CONSTRAINT community_contributions_pkey PRIMARY KEY (id);


--
-- TOC entry 3429 (class 2606 OID 32858)
-- Name: community_projects community_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_projects
    ADD CONSTRAINT community_projects_pkey PRIMARY KEY (id);


--
-- TOC entry 3431 (class 2606 OID 32880)
-- Name: community_votes community_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_votes
    ADD CONSTRAINT community_votes_pkey PRIMARY KEY (id);


--
-- TOC entry 3423 (class 2606 OID 32815)
-- Name: community_wallets community_wallets_community_id_wallet_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_wallets
    ADD CONSTRAINT community_wallets_community_id_wallet_id_key UNIQUE (community_id, wallet_id);


--
-- TOC entry 3425 (class 2606 OID 32813)
-- Name: community_wallets community_wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_wallets
    ADD CONSTRAINT community_wallets_pkey PRIMARY KEY (id);


--
-- TOC entry 3413 (class 2606 OID 24591)
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- TOC entry 3415 (class 2606 OID 24593)
-- Name: transactions transactions_reference_number_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_reference_number_key UNIQUE (reference_number);


--
-- TOC entry 3393 (class 2606 OID 16418)
-- Name: users unique_email; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT unique_email UNIQUE (email);


--
-- TOC entry 3419 (class 2606 OID 32794)
-- Name: user_communities user_communities_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_communities
    ADD CONSTRAINT user_communities_pkey PRIMARY KEY (id);


--
-- TOC entry 3421 (class 2606 OID 32796)
-- Name: user_communities user_communities_user_id_community_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_communities
    ADD CONSTRAINT user_communities_user_id_community_id_key UNIQUE (user_id, community_id);


--
-- TOC entry 3395 (class 2606 OID 16410)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 3397 (class 2606 OID 16422)
-- Name: users users_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_number_key UNIQUE (phone_number);


--
-- TOC entry 3399 (class 2606 OID 16408)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3433 (class 2606 OID 32904)
-- Name: vote_casts vote_casts_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vote_casts
    ADD CONSTRAINT vote_casts_pkey PRIMARY KEY (id);


--
-- TOC entry 3435 (class 2606 OID 32906)
-- Name: vote_casts vote_casts_vote_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vote_casts
    ADD CONSTRAINT vote_casts_vote_id_user_id_key UNIQUE (vote_id, user_id);


--
-- TOC entry 3402 (class 2606 OID 16494)
-- Name: wallets wallets_display_number_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_display_number_key UNIQUE (display_number);


--
-- TOC entry 3404 (class 2606 OID 16477)
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- TOC entry 3406 (class 2606 OID 16479)
-- Name: wallets wallets_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_key UNIQUE (user_id);


--
-- TOC entry 3408 (class 2606 OID 16481)
-- Name: wallets wallets_wallet_number_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_wallet_number_key UNIQUE (wallet_number);


--
-- TOC entry 3409 (class 1259 OID 24605)
-- Name: idx_transactions_destination_wallet; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_destination_wallet ON public.transactions USING btree (destination_wallet_id);


--
-- TOC entry 3410 (class 1259 OID 24606)
-- Name: idx_transactions_reference; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_reference ON public.transactions USING btree (reference_number);


--
-- TOC entry 3411 (class 1259 OID 24604)
-- Name: idx_transactions_source_wallet; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_transactions_source_wallet ON public.transactions USING btree (source_wallet_id);


--
-- TOC entry 3390 (class 1259 OID 16419)
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- TOC entry 3391 (class 1259 OID 16426)
-- Name: idx_users_reset_token; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_users_reset_token ON public.users USING btree (reset_token);


--
-- TOC entry 3400 (class 1259 OID 16487)
-- Name: idx_wallets_user_id; Type: INDEX; Schema: public; Owner: admin
--

CREATE INDEX idx_wallets_user_id ON public.wallets USING btree (user_id);


--
-- TOC entry 3453 (class 2620 OID 16489)
-- Name: users after_user_insert; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER after_user_insert AFTER INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.create_wallet_for_user();


--
-- TOC entry 3454 (class 2620 OID 16491)
-- Name: wallets set_wallet_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER set_wallet_updated_at BEFORE UPDATE ON public.wallets FOR EACH ROW EXECUTE FUNCTION public.update_wallet_timestamp();


--
-- TOC entry 3439 (class 2606 OID 32780)
-- Name: communities communities_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.communities
    ADD CONSTRAINT communities_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.communities(id) ON DELETE SET NULL;


--
-- TOC entry 3444 (class 2606 OID 32842)
-- Name: community_contributions community_contributions_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_contributions
    ADD CONSTRAINT community_contributions_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.communities(id) ON DELETE CASCADE;


--
-- TOC entry 3445 (class 2606 OID 32837)
-- Name: community_contributions community_contributions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_contributions
    ADD CONSTRAINT community_contributions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3446 (class 2606 OID 32859)
-- Name: community_projects community_projects_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_projects
    ADD CONSTRAINT community_projects_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.communities(id) ON DELETE CASCADE;


--
-- TOC entry 3447 (class 2606 OID 32864)
-- Name: community_projects community_projects_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_projects
    ADD CONSTRAINT community_projects_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 3448 (class 2606 OID 32881)
-- Name: community_votes community_votes_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_votes
    ADD CONSTRAINT community_votes_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.communities(id) ON DELETE CASCADE;


--
-- TOC entry 3449 (class 2606 OID 32891)
-- Name: community_votes community_votes_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_votes
    ADD CONSTRAINT community_votes_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3450 (class 2606 OID 32886)
-- Name: community_votes community_votes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_votes
    ADD CONSTRAINT community_votes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.community_projects(id) ON DELETE CASCADE;


--
-- TOC entry 3442 (class 2606 OID 32816)
-- Name: community_wallets community_wallets_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_wallets
    ADD CONSTRAINT community_wallets_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.communities(id) ON DELETE CASCADE;


--
-- TOC entry 3443 (class 2606 OID 32821)
-- Name: community_wallets community_wallets_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.community_wallets
    ADD CONSTRAINT community_wallets_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- TOC entry 3437 (class 2606 OID 24599)
-- Name: transactions transactions_destination_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_destination_wallet_id_fkey FOREIGN KEY (destination_wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- TOC entry 3438 (class 2606 OID 24594)
-- Name: transactions transactions_source_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_source_wallet_id_fkey FOREIGN KEY (source_wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- TOC entry 3440 (class 2606 OID 32802)
-- Name: user_communities user_communities_community_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_communities
    ADD CONSTRAINT user_communities_community_id_fkey FOREIGN KEY (community_id) REFERENCES public.communities(id) ON DELETE CASCADE;


--
-- TOC entry 3441 (class 2606 OID 32797)
-- Name: user_communities user_communities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_communities
    ADD CONSTRAINT user_communities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3451 (class 2606 OID 32912)
-- Name: vote_casts vote_casts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vote_casts
    ADD CONSTRAINT vote_casts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3452 (class 2606 OID 32907)
-- Name: vote_casts vote_casts_vote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vote_casts
    ADD CONSTRAINT vote_casts_vote_id_fkey FOREIGN KEY (vote_id) REFERENCES public.community_votes(id) ON DELETE CASCADE;


--
-- TOC entry 3436 (class 2606 OID 16482)
-- Name: wallets wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Completed on 2025-09-26 21:56:43 UTC

--
-- PostgreSQL database dump complete
--

\unrestrict v7Tkwrg2sr0bmu6r90vZCAmqupYo8Cvhi3LxhiSMpcT3LnP5hnrHWtdD0qbY8Uv

