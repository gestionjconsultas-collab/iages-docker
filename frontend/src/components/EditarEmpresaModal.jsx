// frontend/src/components/EditarEmpresaModal.jsx
import React, { useState } from 'react';
import { X, Building2, Mail, Save, Trash2, Plus, Hash, FileText, Key, Phone, User, Badge, MapPin, Briefcase, Tags } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

const ListaEditable = ({ titulo, icono: Icono, items, setItems, placeholder }) => {
    const [nuevoItem, setNuevoItem] = useState('');

    const agregarItem = () => {
        if (!nuevoItem.trim()) return;
        if (items.includes(nuevoItem.trim())) {
            toast.error('Este elemento ya está agregado');
            return;
        }
        setItems([...items, nuevoItem.trim()]);
        setNuevoItem('');
    };

    const eliminarItem = (itemAEliminar) => {
        setItems(items.filter(i => i !== itemAEliminar));
    };

    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
                {titulo}
            </label>
            {items.length > 0 && (
                <div className="space-y-2 mb-3">
                    {items.map((item, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-200">
                            <Icono className="w-4 h-4 text-gray-600 min-w-[16px] mt-0.5" />
                            <span className="flex-1 text-sm text-gray-700 break-words">{item}</span>
                            <button
                                onClick={() => eliminarItem(item)}
                                className="text-red-500 hover:text-red-700 p-1 rounded transition flex-shrink-0"
                                title="Eliminar"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
            <div className="flex gap-2">
                <input
                    type="text"
                    value={nuevoItem}
                    onChange={(e) => setNuevoItem(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && agregarItem()}
                    placeholder={placeholder}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 text-sm"
                />
                <button
                    onClick={agregarItem}
                    className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition flex items-center gap-1.5 text-sm font-medium flex-shrink-0"
                >
                    <Plus className="w-4 h-4" />
                    Agregar
                </button>
            </div>
        </div>
    );
};

const ListaAdministradoresEditable = ({ administradores, setAdministradores }) => {
    const [nuevoNombre, setNuevoNombre] = useState('');
    const [nuevoCif, setNuevoCif] = useState('');

    const agregarAdmin = () => {
        if (!nuevoNombre.trim()) {
            toast.error('El nombre es obligatorio');
            return;
        }
        setAdministradores([...administradores, { nombre: nuevoNombre.trim(), cif: nuevoCif.trim() }]);
        setNuevoNombre('');
        setNuevoCif('');
    };

    const eliminarAdmin = (indexAEliminar) => {
        setAdministradores(administradores.filter((_, idx) => idx !== indexAEliminar));
    };

    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
                Administradores
            </label>
            {administradores && administradores.length > 0 && (
                <div className="space-y-2 mb-3 max-h-[150px] overflow-y-auto">
                    {administradores.map((admin, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-200">
                            <User className="w-4 h-4 text-gray-600 min-w-[16px] mt-0.5" />
                            <div className="flex-1 flex flex-col">
                                <span className="text-sm font-medium text-gray-800 break-words">{admin.nombre}</span>
                                {admin.cif && <span className="text-xs text-gray-500 font-mono">CIF: {admin.cif}</span>}
                            </div>
                            <button
                                onClick={() => eliminarAdmin(idx)}
                                className="text-red-500 hover:text-red-700 p-1 rounded transition flex-shrink-0"
                                title="Eliminar admin"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
            <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                    <div className="flex-1 relative">
                        <User className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={nuevoNombre}
                            onChange={(e) => setNuevoNombre(e.target.value)}
                            placeholder="Nombre del administrador"
                            className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 text-sm"
                        />
                    </div>
                    <div className="flex-1 relative">
                        <FileText className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={nuevoCif}
                            onChange={(e) => setNuevoCif(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && agregarAdmin()}
                            placeholder="CIF (Opcional)"
                            className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 text-sm"
                        />
                    </div>
                </div>
                <button
                    onClick={agregarAdmin}
                    className="self-end px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition flex items-center gap-1.5 text-sm font-medium flex-shrink-0"
                >
                    <Plus className="w-4 h-4" />
                    Agregar
                </button>
            </div>
        </div>
    );
};

export default function EditarEmpresaModal({ empresa, onClose, onEmpresaActualizada }) {
    const [formData, setFormData] = useState({
        email: empresa.email || '',
        cuenta_cotizacion: empresa.cuenta_cotizacion || '',
        saltra_cert_secret: empresa.saltra_cert_secret || '',
        codigo_empresa: empresa.codigo_empresa || '',
        telefono: empresa.telefono || '',
        nombre_administrador: empresa.nombre_administrador || '',
        apellido_administrador: empresa.apellido_administrador || '',
        nif_administrador: empresa.nif_administrador || '',
        provincia: empresa.provincia || '',
        municipio: empresa.municipio || '',
        codigo_postal: empresa.codigo_postal || '',
        direccion: empresa.direccion || '',
        direccion_centros_trabajo_str: empresa.direccion_centros_trabajo_str || '',
        convenio_numero: empresa.convenio_numero || '',
        convenio_nombre: empresa.convenio_nombre || '',
        epigrafe_iae_str: empresa.epigrafe_iae_str || '',
        cnae_2009_str: empresa.cnae_2009_str || '',
        cnae_2025_str: empresa.cnae_2025_str || ''
    });
    const [direccionesSociedad, setDireccionesSociedad] = useState(empresa.direcciones_sociedad || []);
    const [direccionesCentros, setDireccionesCentros] = useState(empresa.direcciones_centros_trabajo || []);
    const [epigrafesIae, setEpigrafesIae] = useState(empresa.epigrafes_iae || []);
    const [cnaes2009, setCnaes2009] = useState(empresa.cnaes_2009 || []);
    const [cnaes2025, setCnaes2025] = useState(empresa.cnaes_2025 || []);
    const [administradores, setAdministradores] = useState(empresa.administradores || []);

    const [emailsExtra, setEmailsExtra] = useState(empresa.emails_extra || []);
    const [nuevoEmailExtra, setNuevoEmailExtra] = useState('');
    const [guardando, setGuardando] = useState(false);

    const handleGuardarEmail = async () => {
        if (formData.email === empresa.email) return; // No cambió

        try {
            await axios.post(
                `/api/empresas/${empresa.id}/actualizar-email`,
                { email: formData.email },
                { withCredentials: true }
            );
            toast.success('✅ Email principal actualizado');
        } catch (error) {
            toast.error('Error al actualizar email');
            throw error;
        }
    };

    const handleGuardarCuentaCotizacion = async () => {
        if (formData.cuenta_cotizacion === empresa.cuenta_cotizacion) return; // No cambió

        try {
            await axios.post(
                `/api/empresas/${empresa.id}/actualizar-cuenta-cotizacion`,
                { cuenta_cotizacion: formData.cuenta_cotizacion },
                { withCredentials: true }
            );
            toast.success('✅ Cuenta de cotización actualizada');
        } catch (error) {
            toast.error('Error al actualizar cuenta de cotización');
            throw error;
        }
    };

    const handleGuardarCertSecret = async () => {
        if (formData.saltra_cert_secret === empresa.saltra_cert_secret) return; // No cambió

        try {
            await axios.post(
                `/api/empresas/${empresa.id}/actualizar-cert-secret`,
                { saltra_cert_secret: formData.saltra_cert_secret },
                { withCredentials: true }
            );
            toast.success('✅ Certificado Saltra actualizado');
        } catch (error) {
            toast.error('Error al actualizar certificado Saltra');
            throw error;
        }
    };

    const handleGuardarExtras = async () => {
        try {
            await axios.post(
                `/api/empresas/${empresa.id}/actualizar-campos-extra`,
                {
                    codigo_empresa: formData.codigo_empresa,
                    telefono: formData.telefono,
                    nombre_administrador: formData.nombre_administrador,
                    apellido_administrador: formData.apellido_administrador,
                    nif_administrador: formData.nif_administrador,
                    provincia: formData.provincia,
                    municipio: formData.municipio,
                    codigo_postal: formData.codigo_postal,
                    direccion: formData.direccion,
                    direccion_centros_trabajo_str: formData.direccion_centros_trabajo_str,
                    convenio_numero: formData.convenio_numero,
                    convenio_nombre: formData.convenio_nombre,
                    epigrafe_iae_str: formData.epigrafe_iae_str,
                    cnae_2009_str: formData.cnae_2009_str,
                    cnae_2025_str: formData.cnae_2025_str,
                    direcciones_sociedad: direccionesSociedad,
                    direcciones_centros_trabajo: direccionesCentros,
                    epigrafes_iae: epigrafesIae,
                    cnaes_2009: cnaes2009,
                    cnaes_2025: cnaes2025,
                    administradores: administradores
                },
                { withCredentials: true }
            );
        } catch (error) {
            toast.error('Error al actualizar datos extras de la empresa');
            throw error;
        }
    };

    const handleGuardar = async () => {
        setGuardando(true);
        try {
            await handleGuardarEmail();
            await handleGuardarCuentaCotizacion();
            await handleGuardarCertSecret();
            await handleGuardarExtras();

            onEmpresaActualizada();
            onClose();
        } catch (error) {
            console.error('Error al guardar:', error);
        } finally {
            setGuardando(false);
        }
    };

    const agregarEmailExtra = async () => {
        if (!nuevoEmailExtra || !nuevoEmailExtra.includes('@')) {
            toast.error('Email inválido');
            return;
        }

        if (emailsExtra.includes(nuevoEmailExtra)) {
            toast.error('Este email ya está agregado');
            return;
        }

        try {
            const response = await axios.post(
                `/api/empresas/${empresa.id}/agregar-email`,
                { email: nuevoEmailExtra },
                { withCredentials: true }
            );

            if (response.data.success) {
                setEmailsExtra([...emailsExtra, nuevoEmailExtra]);
                setNuevoEmailExtra('');
                toast.success('✅ Email agregado');
            }
        } catch (error) {
            toast.error('Error al agregar email');
        }
    };

    const eliminarEmailExtra = async (emailAEliminar) => {
        try {
            const response = await axios.post(
                `/api/empresas/${empresa.id}/eliminar-email`,
                { email: emailAEliminar },
                { withCredentials: true }
            );

            if (response.data.success) {
                setEmailsExtra(emailsExtra.filter(e => e !== emailAEliminar));
                toast.success('✅ Email eliminado');
            }
        } catch (error) {
            toast.error('Error al eliminar email');
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-500 to-blue-600 text-white sticky top-0">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <Building2 className="w-5 h-5" />
                        Editar Empresa
                    </h3>
                    <button onClick={onClose} className="hover:bg-blue-700 rounded p-1 transition">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-5">
                    {/* Nombre (readonly) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Razón Social
                        </label>
                        <div className="relative">
                            <Building2 className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={empresa.nombre}
                                disabled
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">El nombre no se puede modificar</p>
                    </div>

                    {/* NIF (readonly) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            NIF/CIF de la Empresa
                        </label>
                        <div className="relative">
                            <FileText className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={empresa.nif}
                                disabled
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600 font-mono"
                            />
                        </div>
                    </div>

                    {/* Código de Empresa */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Código de Empresa
                        </label>
                        <div className="relative">
                            <Badge className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={formData.codigo_empresa}
                                onChange={(e) => setFormData({ ...formData, codigo_empresa: e.target.value })}
                                placeholder="Ej: EMP-001"
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>


                    {/* Teléfono */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Teléfono
                        </label>
                        <div className="relative">
                            <Phone className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={formData.telefono}
                                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                                placeholder="Teléfono de contacto"
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>


                    {/* Certificado Saltra DEHU */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Certificado Saltra (Cert-Secret)
                        </label>
                        <div className="relative">
                            <Key className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                value={formData.saltra_cert_secret}
                                onChange={(e) => setFormData({ ...formData, saltra_cert_secret: e.target.value })}
                                placeholder="2d371d5ab66f2be540fecbdcf39bfae4bc731394"
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 font-mono text-sm"
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            Cert-Secret del certificado registrado en Saltra para notificaciones DEHU
                        </p>
                    </div>

                    {/* Email Principal */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Email Principal
                        </label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                            <input
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                placeholder="contacto@empresa.com"
                                className="w-full pl-9 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>

                    {/* SECCIÓN ADMINISTRADOR */}
                    <div className="pt-4 border-t border-gray-100">
                        <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2 mb-3">
                            <User className="w-4 h-4 text-blue-500" />
                            Datos del Administrador
                        </h4>
                        <div className="grid grid-cols-1 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">Nombre (Separa con ;)</label>
                                <input
                                    type="text"
                                    value={formData.nombre_administrador}
                                    onChange={(e) => setFormData({ ...formData, nombre_administrador: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Juan; Maria"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">Apellidos (Separa con ;)</label>
                                <input
                                    type="text"
                                    value={formData.apellido_administrador}
                                    onChange={(e) => setFormData({ ...formData, apellido_administrador: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="García; Pérez"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">NIF/NIE (Separa con ;)</label>
                                <input
                                    type="text"
                                    value={formData.nif_administrador}
                                    onChange={(e) => setFormData({ ...formData, nif_administrador: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
                                    placeholder="12345678Z; 87654321X"
                                />
                            </div>
                        </div>
                    </div>

                    {/* SECCIÓN LOCALIZACIÓN */}
                    <div className="pt-4 border-t border-gray-100">
                        <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2 mb-3">
                            <MapPin className="w-4 h-4 text-green-500" />
                            Localización y Sede
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-1">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Provincia</label>
                                <input
                                    type="text"
                                    value={formData.provincia}
                                    onChange={(e) => setFormData({ ...formData, provincia: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Ej: Madrid"
                                />
                            </div>
                            <div className="col-span-1">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Municipio</label>
                                <input
                                    type="text"
                                    value={formData.municipio}
                                    onChange={(e) => setFormData({ ...formData, municipio: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Ej: Alcorcón"
                                />
                            </div>
                            <div className="col-span-1">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Código Postal</label>
                                <input
                                    type="text"
                                    value={formData.codigo_postal}
                                    onChange={(e) => setFormData({ ...formData, codigo_postal: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
                                    placeholder="28001"
                                />
                            </div>
                            <div className="col-span-2">
                                <label className="block text-xs font-medium text-gray-500 mb-1">Dirección Social Completa</label>
                                <input
                                    type="text"
                                    value={formData.direccion}
                                    onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Calle, número, piso..."
                                />
                            </div>
                        </div>
                    </div>

                    {/* SECCIÓN LABORAL / CONVENIO */}
                    <div className="pt-4 border-t border-gray-100">
                        <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2 mb-3">
                            <Briefcase className="w-4 h-4 text-orange-500" />
                            Configuración Laboral
                        </h4>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">Cuenta de Cotización</label>
                                <input
                                    type="text"
                                    value={formData.cuenta_cotizacion}
                                    onChange={(e) => setFormData({ ...formData, cuenta_cotizacion: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
                                    placeholder="11/1234567/89"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="col-span-1">
                                    <label className="block text-xs font-medium text-gray-500 mb-1">Nº Convenio</label>
                                    <input
                                        type="text"
                                        value={formData.convenio_numero}
                                        onChange={(e) => setFormData({ ...formData, convenio_numero: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                        placeholder="Código"
                                    />
                                </div>
                                <div className="col-span-1">
                                    <label className="block text-xs font-medium text-gray-500 mb-1">Nombre Convenio</label>
                                    <input
                                        type="text"
                                        value={formData.convenio_nombre}
                                        onChange={(e) => setFormData({ ...formData, convenio_nombre: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                        placeholder="Descripción"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* CÓDIGOS ACTIVIDAD */}
                    <div className="pt-4 border-t border-gray-100">
                        <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2 mb-3">
                            <Tags className="w-4 h-4 text-purple-500" />
                            Actividad y Epígrafes
                        </h4>
                        <div className="grid grid-cols-1 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">EPÍGRAFE IAE</label>
                                <input
                                    type="text"
                                    value={formData.epigrafe_iae_str}
                                    onChange={(e) => setFormData({ ...formData, epigrafe_iae_str: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Ej: 692"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 mb-1">CNAE 2009</label>
                                    <input
                                        type="text"
                                        value={formData.cnae_2009_str}
                                        onChange={(e) => setFormData({ ...formData, cnae_2009_str: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                        placeholder="6920"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 mb-1">CNAE 2025</label>
                                    <input
                                        type="text"
                                        value={formData.cnae_2025_str}
                                        onChange={(e) => setFormData({ ...formData, cnae_2025_str: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                        placeholder="6920"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-500 mb-1">Centros de Trabajo (Resumen)</label>
                                <input
                                    type="text"
                                    value={formData.direccion_centros_trabajo_str}
                                    onChange={(e) => setFormData({ ...formData, direccion_centros_trabajo_str: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                    placeholder="Ej: Madrid, Barcelona"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Emails Extra */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Emails Adicionales
                        </label>

                        {/* Lista de emails extra */}
                        {emailsExtra.length > 0 && (
                            <div className="space-y-2 mb-3">
                                {emailsExtra.map((email, idx) => (
                                    <div key={idx} className="flex items-center gap-2 p-2.5 bg-blue-50 rounded-lg border border-blue-200">
                                        <Mail className="w-4 h-4 text-blue-600" />
                                        <span className="flex-1 text-sm text-gray-700">{email}</span>
                                        <button
                                            onClick={() => eliminarEmailExtra(email)}
                                            className="text-red-600 hover:text-red-800 hover:bg-red-100 p-1 rounded transition"
                                            title="Eliminar email"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Agregar nuevo email extra */}
                        <div className="flex gap-2">
                            <input
                                type="email"
                                value={nuevoEmailExtra}
                                onChange={(e) => setNuevoEmailExtra(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && agregarEmailExtra()}
                                placeholder="nuevo@email.com"
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
                            />
                            <button
                                onClick={agregarEmailExtra}
                                className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center gap-1.5 text-sm font-medium"
                            >
                                <Plus className="w-4 h-4" />
                                Agregar
                            </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">Presiona Enter para agregar rápidamente</p>
                    </div>

                </div>

                {/* Footer */}
                <div className="flex gap-3 p-4 border-t bg-gray-50 sticky bottom-0">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-100 transition font-medium"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleGuardar}
                        disabled={guardando}
                        className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2 font-medium"
                    >
                        {guardando ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Guardando...
                            </>
                        ) : (
                            <>
                                <Save className="w-4 h-4" />
                                Guardar Cambios
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
